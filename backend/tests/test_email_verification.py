"""
Test Email Verification Enforcement and Google OAuth
Iteration 20: P2 - Email verification flow enforcement

Tests:
1. Signup creates unverified user (email_verified=false)
2. Login works for unverified users
3. GET /api/auth/me returns email_verified field
4. 403 enforcement on protected endpoints for unverified users
5. 200 on read-only endpoints for unverified users
6. Verified user regression tests
7. Google OAuth endpoints
8. Resend verification endpoint
"""

import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
VERIFIED_USER_EMAIL = "test_refactor@example.com"
VERIFIED_USER_PASSWORD = "Test123456!"

# Generate unique unverified user for this test run
UNVERIFIED_USER_EMAIL = f"unverified_test_{uuid.uuid4().hex[:8]}@example.com"
UNVERIFIED_USER_PASSWORD = "Test123456!"
UNVERIFIED_USER_NAME = "Unverified Test User"


class TestEmailVerificationSetup:
    """Setup tests - create unverified user and get tokens"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def test_health_check(self, session):
        """Verify API is accessible"""
        response = session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")
    
    def test_signup_creates_unverified_user(self, session):
        """POST /api/auth/signup - creates unverified user (email_verified=false)"""
        response = session.post(f"{BASE_URL}/api/auth/signup", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD,
            "name": UNVERIFIED_USER_NAME
        })
        assert response.status_code == 200, f"Signup failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        
        # Verify user is unverified
        user = data["user"]
        assert user["email"] == UNVERIFIED_USER_EMAIL
        assert user["email_verified"] == False, "New user should be unverified"
        print(f"✓ Signup created unverified user: {user['email']}, email_verified={user['email_verified']}")
        
        # Store token for later tests
        pytest.unverified_token = data["access_token"]


class TestUnverifiedUserLogin:
    """Test that unverified users can still login"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def test_login_works_for_unverified_user(self, session):
        """POST /api/auth/login - works for unverified users"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Check if 2FA is required (skip if so)
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email_verified"] == False
        print(f"✓ Unverified user can login: {data['user']['email']}")
        
        # Store token
        pytest.unverified_token = data["access_token"]
    
    def test_get_me_returns_email_verified_field(self, session):
        """GET /api/auth/me - returns email_verified field"""
        token = getattr(pytest, 'unverified_token', None)
        if not token:
            pytest.skip("No unverified token available")
        
        response = session.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "email_verified" in data, "email_verified field missing from /auth/me response"
        assert data["email_verified"] == False
        print(f"✓ GET /auth/me returns email_verified={data['email_verified']}")


class TestUnverifiedUser403Enforcement:
    """Test that unverified users get 403 on protected operations"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def unverified_headers(self, session):
        """Get auth headers for unverified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not login unverified user")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_unverified_user_403_on_create_project(self, session, unverified_headers):
        """POST /api/projects - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/projects",
            headers=unverified_headers,
            json={"name": "Test Project", "description": "Test"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/projects returns 403 for unverified user: {data.get('detail')}")
    
    def test_unverified_user_403_on_ai_generate(self, session, unverified_headers):
        """POST /api/ai/generate - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/ai/generate",
            headers=unverified_headers,
            json={"prompt": "test", "project_id": "fake-id", "task_type": "code_generation"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/ai/generate returns 403 for unverified user: {data.get('detail')}")
    
    def test_unverified_user_403_on_ai_execute(self, session, unverified_headers):
        """POST /api/ai/execute - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/ai/execute",
            headers=unverified_headers,
            json={"prompt": "test", "operation": "code_generation"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/ai/execute returns 403 for unverified user: {data.get('detail')}")
    
    def test_unverified_user_403_on_sandbox_execute(self, session, unverified_headers):
        """POST /api/autonomous/sandbox/execute - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/autonomous/sandbox/execute",
            headers=unverified_headers,
            json={"code": "print('hello')", "language": "python"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/autonomous/sandbox/execute returns 403 for unverified user: {data.get('detail')}")
    
    def test_unverified_user_403_on_validate_loop(self, session, unverified_headers):
        """POST /api/autonomous/validate-loop - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/autonomous/validate-loop",
            headers=unverified_headers,
            json={"code": "def test(): pass", "filename": "test.py", "language": "python"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/autonomous/validate-loop returns 403 for unverified user: {data.get('detail')}")
    
    def test_unverified_user_403_on_deploy(self, session, unverified_headers):
        """POST /api/deploy/{id} - unverified user gets 403"""
        response = session.post(
            f"{BASE_URL}/api/deploy/fake-project-id",
            headers=unverified_headers
        )
        # Should be 403 for email verification, not 404 for project not found
        # The require_verified_email dependency runs before project lookup
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email verification" in data.get("detail", "").lower() or "verify" in data.get("detail", "").lower()
        print(f"✓ POST /api/deploy/{{id}} returns 403 for unverified user: {data.get('detail')}")


class TestUnverifiedUserReadAllowed:
    """Test that unverified users can still read (GET) certain endpoints"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def unverified_headers(self, session):
        """Get auth headers for unverified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not login unverified user")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_unverified_user_can_get_projects(self, session, unverified_headers):
        """GET /api/projects - unverified user gets 200 (read allowed)"""
        response = session.get(
            f"{BASE_URL}/api/projects",
            headers=unverified_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/projects returns 200 for unverified user (found {len(data)} projects)")
    
    def test_unverified_user_can_get_credits(self, session, unverified_headers):
        """GET /api/user/credits - unverified user gets 200 (read allowed)"""
        response = session.get(
            f"{BASE_URL}/api/user/credits",
            headers=unverified_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "credits" in data or "plan" in data
        print(f"✓ GET /api/user/credits returns 200 for unverified user: {data}")
    
    def test_unverified_user_can_get_plans(self, session, unverified_headers):
        """GET /api/plans - unverified user gets 200 (read allowed)"""
        response = session.get(
            f"{BASE_URL}/api/plans",
            headers=unverified_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "plans" in data or isinstance(data, list)
        print(f"✓ GET /api/plans returns 200 for unverified user")
    
    def test_unverified_user_can_get_feedback_stats(self, session, unverified_headers):
        """GET /api/autonomous/feedback/stats - unverified user gets 200 (read allowed)"""
        response = session.get(
            f"{BASE_URL}/api/autonomous/feedback/stats",
            headers=unverified_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        print(f"✓ GET /api/autonomous/feedback/stats returns 200 for unverified user: {data}")


class TestResendVerification:
    """Test resend verification endpoint"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def unverified_headers(self, session):
        """Get auth headers for unverified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not login unverified user")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_resend_verification_endpoint_exists(self, session, unverified_headers):
        """POST /api/auth/resend-verification - endpoint exists and responds"""
        response = session.post(
            f"{BASE_URL}/api/auth/resend-verification",
            headers=unverified_headers
        )
        # Should return 200 with message, or 400 if already verified
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}: {response.text}"
        data = response.json()
        if response.status_code == 200:
            assert "message" in data
            print(f"✓ POST /api/auth/resend-verification returns 200: {data.get('message')}")
        else:
            print(f"✓ POST /api/auth/resend-verification returns 400 (already verified): {data}")


class TestGoogleOAuth:
    """Test Google OAuth endpoints"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def test_google_oauth_redirect(self, session):
        """GET /api/auth/google - redirects to Google OAuth (302/307)"""
        response = session.get(
            f"{BASE_URL}/api/auth/google",
            allow_redirects=False
        )
        # Should redirect to Google
        assert response.status_code in [302, 307], f"Expected redirect, got {response.status_code}: {response.text}"
        
        location = response.headers.get("Location", "")
        assert "accounts.google.com" in location, f"Expected Google redirect, got: {location}"
        assert "client_id=" in location, "Missing client_id in redirect URL"
        print(f"✓ GET /api/auth/google redirects to Google: {location[:100]}...")
    
    def test_google_callback_endpoint_exists(self, session):
        """POST /api/auth/google/callback - endpoint exists and responds"""
        # Send a fake code - should fail with 401 (invalid code) not 404 (not found)
        response = session.post(
            f"{BASE_URL}/api/auth/google/callback",
            json={"code": "fake_authorization_code"}
        )
        # Should return 401 (invalid code) or 503 (not configured), not 404
        assert response.status_code in [401, 503, 400, 500], f"Unexpected status: {response.status_code}: {response.text}"
        print(f"✓ POST /api/auth/google/callback endpoint exists (returns {response.status_code})")


class TestVerifiedUserRegression:
    """Regression tests - verified user can still perform protected operations"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def verified_headers(self, session):
        """Get auth headers for verified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VERIFIED_USER_EMAIL,
            "password": VERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login verified user: {response.text}")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_verified_user_is_verified(self, session, verified_headers):
        """Verify test user is actually verified"""
        response = session.get(
            f"{BASE_URL}/api/auth/me",
            headers=verified_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("email_verified") == True, f"Test user should be verified: {data}"
        print(f"✓ Verified user has email_verified=True")
    
    def test_verified_user_can_create_project(self, session, verified_headers):
        """POST /api/projects - verified user gets 200"""
        project_name = f"Test Project {uuid.uuid4().hex[:8]}"
        response = session.post(
            f"{BASE_URL}/api/projects",
            headers=verified_headers,
            json={"name": project_name, "description": "Test project for email verification testing"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data.get("name") == project_name
        print(f"✓ Verified user can create project: {data.get('id')}")
        
        # Store project ID for later tests
        pytest.test_project_id = data.get("id")
    
    def test_verified_user_can_use_ai_execute(self, session, verified_headers):
        """POST /api/ai/execute - verified user gets 200 (or 402/429 for credits/rate limit)"""
        response = session.post(
            f"{BASE_URL}/api/ai/execute",
            headers=verified_headers,
            json={"prompt": "Write a hello world function", "operation": "code_generation"}
        )
        # 200 = success, 402 = insufficient credits, 429 = rate limit
        # All are valid responses for a verified user (not 403)
        assert response.status_code in [200, 402, 429], f"Expected 200/402/429, got {response.status_code}: {response.text}"
        print(f"✓ Verified user can access AI execute (status: {response.status_code})")
    
    def test_verified_user_can_use_sandbox(self, session, verified_headers):
        """POST /api/autonomous/sandbox/execute - verified user gets 200 (or 402/429)"""
        response = session.post(
            f"{BASE_URL}/api/autonomous/sandbox/execute",
            headers=verified_headers,
            json={"code": "print('hello')", "language": "python"}
        )
        # 200 = success, 402 = insufficient credits, 429 = rate limit
        assert response.status_code in [200, 402, 429], f"Expected 200/402/429, got {response.status_code}: {response.text}"
        print(f"✓ Verified user can access sandbox (status: {response.status_code})")


class TestRegressionEndpoints:
    """Additional regression tests for other endpoints"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def verified_headers(self, session):
        """Get auth headers for verified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": VERIFIED_USER_EMAIL,
            "password": VERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip(f"Could not login verified user: {response.text}")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_health_endpoint(self, session):
        """GET /api/health - works"""
        response = session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        print("✓ GET /api/health works")
    
    def test_ai_models_endpoint(self, session, verified_headers):
        """GET /api/ai/models - works"""
        response = session.get(
            f"{BASE_URL}/api/ai/models",
            headers=verified_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        print(f"✓ GET /api/ai/models works: {len(data['models'])} models")
    
    def test_plans_endpoint(self, session, verified_headers):
        """GET /api/plans - works"""
        response = session.get(
            f"{BASE_URL}/api/plans",
            headers=verified_headers
        )
        assert response.status_code == 200
        print("✓ GET /api/plans works")
    
    def test_payments_create_order(self, session, verified_headers):
        """POST /api/payments/create-order - works for verified user"""
        response = session.post(
            f"{BASE_URL}/api/payments/create-order",
            headers=verified_headers,
            json={"plan": "standard"}
        )
        # 200 = success (demo mode), 400 = invalid plan, 402 = payment issue
        assert response.status_code in [200, 400, 402], f"Unexpected status: {response.status_code}: {response.text}"
        print(f"✓ POST /api/payments/create-order works (status: {response.status_code})")
    
    def test_feedback_endpoint(self, session, verified_headers):
        """POST /api/autonomous/feedback - works for verified user"""
        response = session.post(
            f"{BASE_URL}/api/autonomous/feedback",
            headers=verified_headers,
            json={"rating": 5, "type": "general", "comment": "Test feedback from email verification tests"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ POST /api/autonomous/feedback works")


class Test403ResponseFormat:
    """Test that 403 responses have the correct format"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def unverified_headers(self, session):
        """Get auth headers for unverified user"""
        response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": UNVERIFIED_USER_EMAIL,
            "password": UNVERIFIED_USER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Could not login unverified user")
        data = response.json()
        if data.get("requires_2fa"):
            pytest.skip("User has 2FA enabled")
        return {"Authorization": f"Bearer {data['access_token']}"}
    
    def test_403_response_includes_descriptive_message(self, session, unverified_headers):
        """403 response includes descriptive message about email verification"""
        response = session.post(
            f"{BASE_URL}/api/projects",
            headers=unverified_headers,
            json={"name": "Test", "description": "Test"}
        )
        assert response.status_code == 403
        data = response.json()
        
        detail = data.get("detail", "")
        # Check for expected message content
        assert "email verification required" in detail.lower() or "verify your email" in detail.lower(), \
            f"403 detail should mention email verification: {detail}"
        print(f"✓ 403 response has descriptive message: {detail}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
