"""
Backend API tests for OAuth authentication flows (Google, GitHub) and Email/Password auth.
Tests cover:
- Google OAuth session exchange endpoint
- GitHub OAuth redirect endpoint  
- Email/password login
- Email/password signup
- /auth/me endpoint
"""

import pytest
import requests
import os
import uuid

# Backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestHealthCheck:
    """Health check to verify backend is running"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed: {data}")

class TestGoogleOAuth:
    """Google OAuth (Emergent Auth) endpoint tests"""
    
    def test_google_session_endpoint_exists(self):
        """POST /api/auth/google/session should exist and return proper error for invalid session"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google/session",
            json={"session_id": "invalid_test_session_123"}
        )
        # Should return 401 (authentication failed) not 404 (not found)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        # Should say "Google authentication failed" not "Not Found"
        assert "Google authentication failed" in data["detail"] or "auth" in data["detail"].lower()
        print(f"✓ Google session endpoint returns appropriate error: {data}")
    
    def test_google_session_missing_session_id(self):
        """POST /api/auth/google/session without session_id should return 422 validation error"""
        response = requests.post(
            f"{BASE_URL}/api/auth/google/session",
            json={}
        )
        # Missing field should return 422 (validation error)
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print(f"✓ Google session endpoint validates required fields")

class TestGitHubOAuth:
    """GitHub OAuth endpoint tests"""
    
    def test_github_login_returns_proper_error(self):
        """GET /api/auth/github should return error about configuration, not crash"""
        response = requests.get(f"{BASE_URL}/api/auth/github", allow_redirects=False)
        # Should return 500 (not configured) with proper message OR redirect (if configured)
        # NOT 404 (not found)
        assert response.status_code != 404, f"GitHub endpoint should not return 404"
        
        if response.status_code == 500:
            # Not configured - check for proper error message
            data = response.json()
            assert "detail" in data
            assert "GitHub OAuth not configured" in data["detail"]
            print(f"✓ GitHub endpoint returns proper configuration error: {data}")
        elif response.status_code in [302, 307]:
            # Configured and redirecting to GitHub
            print(f"✓ GitHub endpoint redirects to GitHub OAuth: {response.headers.get('location', '')}")
        else:
            print(f"GitHub endpoint returned status {response.status_code}: {response.text}")

class TestEmailPasswordAuth:
    """Email/password authentication tests"""
    
    def test_login_success(self):
        """POST /api/auth/login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@cursorcode.ai",
                "password": "Test123456!"
            }
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == "test@cursorcode.ai"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0
        print(f"✓ Email login successful for {data['user']['email']}")
        
        return data
    
    def test_login_invalid_credentials(self):
        """POST /api/auth/login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "wrong@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid credentials properly rejected: {data}")
    
    def test_signup_success(self):
        """POST /api/auth/signup creates new user"""
        unique_email = f"test_{uuid.uuid4().hex[:8]}@cursorcode.ai"
        response = requests.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "name": "Test Signup User",
                "email": unique_email,
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == 200, f"Signup failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["name"] == "Test Signup User"
        print(f"✓ Signup successful for {data['user']['email']}")
    
    def test_signup_duplicate_email(self):
        """POST /api/auth/signup with existing email returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "name": "Duplicate User",
                "email": "test@cursorcode.ai",  # Already exists
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == 400, f"Expected 400 for duplicate email, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "already registered" in data["detail"].lower()
        print(f"✓ Duplicate email properly rejected: {data}")

class TestAuthMe:
    """GET /api/auth/me endpoint tests"""
    
    def test_auth_me_with_valid_token(self):
        """GET /api/auth/me with valid token returns user data"""
        # First login to get token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": "test@cursorcode.ai",
                "password": "Test123456!"
            }
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Now test /auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth me failed: {response.text}"
        data = response.json()
        
        # Validate user data structure
        assert data["email"] == "test@cursorcode.ai"
        assert "id" in data
        assert "name" in data
        assert "plan" in data
        assert "credits" in data
        print(f"✓ Auth me returned user data: {data['email']}, plan: {data['plan']}")
    
    def test_auth_me_without_token(self):
        """GET /api/auth/me without token returns 401/403"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Auth me properly rejects unauthenticated requests")
    
    def test_auth_me_with_invalid_token(self):
        """GET /api/auth/me with invalid token returns 401"""
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401, f"Expected 401 for invalid token, got {response.status_code}"
        print(f"✓ Auth me properly rejects invalid tokens")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
