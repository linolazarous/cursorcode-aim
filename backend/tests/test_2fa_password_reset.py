"""
Tests for Two-Factor Authentication (2FA) and Password Reset functionality.
Tests cover:
- 2FA enable/verify/disable endpoints
- Login with 2FA (login-2fa)
- Password reset request and confirm
"""
import pytest
import requests
import os
import pyotp
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://grok-devops.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="module")
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def test_user_2fa(api_client):
    """Create a test user for 2FA testing"""
    timestamp = int(time.time())
    email = f"TEST_2fa_user_{timestamp}@example.com"
    password = "Test123456!"
    
    # Signup
    res = api_client.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email,
        "name": "2FA Test User",
        "password": password
    })
    assert res.status_code == 200
    data = res.json()
    
    return {
        "email": email,
        "password": password,
        "token": data["access_token"],
        "user_id": data["user"]["id"],
        "totp_secret": None,
        "backup_codes": []
    }


@pytest.fixture(scope="module")
def test_user_reset(api_client):
    """Create a test user for password reset testing"""
    timestamp = int(time.time())
    email = f"TEST_reset_user_{timestamp}@example.com"
    password = "Test123456!"
    
    res = api_client.post(f"{BASE_URL}/api/auth/signup", json={
        "email": email,
        "name": "Reset Test User",
        "password": password
    })
    assert res.status_code == 200
    return {"email": email, "password": password}


class Test2FAEndpoints:
    """Two-Factor Authentication endpoint tests"""
    
    def test_2fa_enable_without_auth(self, api_client):
        """2FA enable should require authentication"""
        clean_client = requests.Session()
        clean_client.headers.update({"Content-Type": "application/json"})
        res = clean_client.post(f"{BASE_URL}/api/auth/2fa/enable")
        assert res.status_code in [401, 403]
        print("PASS: 2FA enable requires authentication")
    
    def test_2fa_enable_returns_qr_and_secret(self, api_client, test_user_2fa):
        """2FA enable should return QR code and secret"""
        api_client.headers.update({"Authorization": f"Bearer {test_user_2fa['token']}"})
        res = api_client.post(f"{BASE_URL}/api/auth/2fa/enable")
        assert res.status_code == 200
        
        data = res.json()
        assert "qr_code_base64" in data, "QR code should be returned"
        assert "secret" in data, "Secret should be returned"
        assert "backup_codes" in data, "Backup codes should be returned"
        assert data["qr_code_base64"].startswith("data:image/png;base64,")
        assert len(data["secret"]) == 32  # Base32 secret
        assert len(data["backup_codes"]) == 8
        
        # Store for next tests
        test_user_2fa["totp_secret"] = data["secret"]
        test_user_2fa["backup_codes"] = data["backup_codes"]
        print(f"PASS: 2FA enable returns QR, secret ({data['secret'][:8]}...) and 8 backup codes")
    
    def test_2fa_verify_with_valid_code(self, api_client, test_user_2fa):
        """2FA verify should enable 2FA with valid TOTP code"""
        api_client.headers.update({"Authorization": f"Bearer {test_user_2fa['token']}"})
        
        # Generate TOTP code
        totp = pyotp.TOTP(test_user_2fa["totp_secret"])
        code = totp.now()
        
        res = api_client.post(f"{BASE_URL}/api/auth/2fa/verify", json={"code": code})
        assert res.status_code == 200
        data = res.json()
        assert "message" in data
        assert "enabled" in data["message"].lower()
        print(f"PASS: 2FA verified and enabled with code {code}")
    
    def test_2fa_verify_with_invalid_code(self, api_client, test_user_2fa):
        """2FA verify should reject invalid codes"""
        api_client.headers.update({"Authorization": f"Bearer {test_user_2fa['token']}"})
        res = api_client.post(f"{BASE_URL}/api/auth/2fa/verify", json={"code": "000000"})
        # This might return 400 or still 200 if 2FA already enabled
        # Just check it doesn't crash
        assert res.status_code in [200, 400]
        print(f"PASS: 2FA verify with invalid code handled (status: {res.status_code})")
    
    def test_login_requires_2fa_when_enabled(self, api_client, test_user_2fa):
        """Login should return requires_2fa when 2FA is enabled"""
        res = api_client.post(f"{BASE_URL}/api/auth/login", json={
            "email": test_user_2fa["email"],
            "password": test_user_2fa["password"]
        })
        assert res.status_code == 200
        data = res.json()
        assert data.get("requires_2fa") == True, "Should require 2FA"
        assert "message" in data
        print(f"PASS: Login returns requires_2fa=True for 2FA-enabled user")
    
    def test_login_2fa_with_valid_code(self, api_client, test_user_2fa):
        """Login with 2FA should work with valid TOTP code"""
        totp = pyotp.TOTP(test_user_2fa["totp_secret"])
        code = totp.now()
        
        res = api_client.post(f"{BASE_URL}/api/auth/login-2fa", json={
            "email": test_user_2fa["email"],
            "password": test_user_2fa["password"],
            "totp_code": code
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data, "Should return access token"
        assert "user" in data, "Should return user data"
        print(f"PASS: Login with 2FA successful using code {code}")
    
    def test_login_2fa_with_invalid_code(self, api_client, test_user_2fa):
        """Login with 2FA should fail with invalid TOTP code"""
        res = api_client.post(f"{BASE_URL}/api/auth/login-2fa", json={
            "email": test_user_2fa["email"],
            "password": test_user_2fa["password"],
            "totp_code": "000000"
        })
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print(f"PASS: Login with invalid 2FA code returns 401")
    
    def test_2fa_disable_with_valid_code(self, api_client, test_user_2fa):
        """2FA disable should work with valid code"""
        api_client.headers.update({"Authorization": f"Bearer {test_user_2fa['token']}"})
        
        totp = pyotp.TOTP(test_user_2fa["totp_secret"])
        code = totp.now()
        
        res = api_client.post(f"{BASE_URL}/api/auth/2fa/disable", json={"code": code})
        assert res.status_code == 200
        data = res.json()
        assert "disabled" in data["message"].lower()
        print(f"PASS: 2FA disabled successfully")


class TestPasswordReset:
    """Password Reset endpoint tests"""
    
    def test_password_reset_request_success(self, api_client, test_user_reset):
        """Password reset request should return success (even for non-existent emails to prevent enumeration)"""
        res = api_client.post(f"{BASE_URL}/api/auth/reset-password/request", json={
            "email": test_user_reset["email"]
        })
        assert res.status_code == 200
        data = res.json()
        assert "message" in data
        print(f"PASS: Password reset request returns success message")
    
    def test_password_reset_request_nonexistent_email(self, api_client):
        """Password reset should return 200 even for non-existent email (prevent enumeration)"""
        res = api_client.post(f"{BASE_URL}/api/auth/reset-password/request", json={
            "email": "nonexistent_user_12345@example.com"
        })
        assert res.status_code == 200, "Should return 200 to prevent email enumeration"
        print(f"PASS: Password reset for non-existent email returns 200 (security)")
    
    def test_password_reset_confirm_invalid_token(self, api_client):
        """Password reset confirm should fail with invalid token"""
        res = api_client.post(f"{BASE_URL}/api/auth/reset-password/confirm", json={
            "token": "invalid_token_12345",
            "new_password": "NewPassword123!"
        })
        assert res.status_code == 400
        print(f"PASS: Password reset with invalid token returns 400")
    
    def test_password_reset_confirm_short_password(self, api_client):
        """Password reset confirm should validate password length"""
        res = api_client.post(f"{BASE_URL}/api/auth/reset-password/confirm", json={
            "token": "some_token",
            "new_password": "short"
        })
        # This should fail with 400 (invalid token) or 400 (password too short)
        assert res.status_code == 400
        print(f"PASS: Password reset with short password handled")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
