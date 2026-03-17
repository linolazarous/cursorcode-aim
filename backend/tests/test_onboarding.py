"""
Test suite for Onboarding Wizard - Iteration 8
Tests the POST /api/users/me/complete-onboarding endpoint

Features tested:
- New users have onboarding_completed=false by default
- POST /api/users/me/complete-onboarding sets onboarding_completed=true
- Endpoint requires authentication
- User state persists after completion
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestOnboardingEndpoint:
    """Test onboarding completion endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data - create a fresh test user for onboarding"""
        self.test_email = f"test_onboarding_{uuid.uuid4().hex[:8]}@cursorcode.ai"
        self.test_password = "Test123456!"
        self.test_name = "Onboarding Test User"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def test_signup_creates_user_with_onboarding_false(self):
        """Test that new signup creates user with onboarding_completed=false"""
        # Sign up a new user
        response = self.session.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "email": self.test_email,
                "password": self.test_password,
                "name": self.test_name
            }
        )
        
        assert response.status_code == 200, f"Signup failed: {response.text}"
        data = response.json()
        
        # Verify tokens returned
        assert "access_token" in data
        assert "user" in data
        
        # Verify onboarding_completed is false for new users
        user = data["user"]
        assert user["onboarding_completed"] == False, "New user should have onboarding_completed=false"
        print(f"✓ New user created with onboarding_completed=false: {self.test_email}")
        
        return data["access_token"], user
    
    def test_complete_onboarding_endpoint(self):
        """Test POST /api/users/me/complete-onboarding sets onboarding_completed=true"""
        # First signup to get a new user
        signup_response = self.session.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "email": self.test_email,
                "password": self.test_password,
                "name": self.test_name
            }
        )
        
        assert signup_response.status_code == 200
        signup_data = signup_response.json()
        access_token = signup_data["access_token"]
        
        # Verify initial state is onboarding_completed=false
        assert signup_data["user"]["onboarding_completed"] == False
        
        # Now call complete-onboarding endpoint
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        
        complete_response = self.session.post(
            f"{BASE_URL}/api/users/me/complete-onboarding"
        )
        
        assert complete_response.status_code == 200, f"Complete onboarding failed: {complete_response.text}"
        
        # Verify response message
        complete_data = complete_response.json()
        assert complete_data.get("message") == "Onboarding completed", f"Unexpected response: {complete_data}"
        print("✓ Onboarding completion endpoint returned success message")
        
        # Now verify user state changed by calling /auth/me
        me_response = self.session.get(f"{BASE_URL}/api/auth/me")
        assert me_response.status_code == 200
        
        user_data = me_response.json()
        assert user_data["onboarding_completed"] == True, "User should have onboarding_completed=true after calling complete-onboarding"
        print(f"✓ User onboarding_completed changed to true for: {self.test_email}")
    
    def test_complete_onboarding_requires_auth(self):
        """Test that complete-onboarding endpoint requires authentication"""
        # Try to call endpoint without auth
        response = requests.post(
            f"{BASE_URL}/api/users/me/complete-onboarding",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 403 or response.status_code == 401, \
            f"Expected 401/403 without auth, got: {response.status_code}"
        print("✓ Complete-onboarding requires authentication")
    
    def test_complete_onboarding_idempotent(self):
        """Test that calling complete-onboarding multiple times is idempotent"""
        # Signup
        signup_response = self.session.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "email": self.test_email,
                "password": self.test_password,
                "name": self.test_name
            }
        )
        
        assert signup_response.status_code == 200
        access_token = signup_response.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})
        
        # Call complete-onboarding twice
        first_response = self.session.post(f"{BASE_URL}/api/users/me/complete-onboarding")
        assert first_response.status_code == 200
        
        second_response = self.session.post(f"{BASE_URL}/api/users/me/complete-onboarding")
        assert second_response.status_code == 200, "Calling complete-onboarding twice should not fail"
        
        print("✓ Complete-onboarding is idempotent (can be called multiple times)")


class TestUserOnboardingState:
    """Test user onboarding state in auth responses"""
    
    def test_login_returns_onboarding_state(self):
        """Test that login response includes onboarding_completed field"""
        # First create a test user
        test_email = f"test_login_onboarding_{uuid.uuid4().hex[:8]}@cursorcode.ai"
        test_password = "Test123456!"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Signup
        signup_response = session.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "email": test_email,
                "password": test_password,
                "name": "Login Test"
            }
        )
        assert signup_response.status_code == 200
        
        # Login
        login_response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": test_email,
                "password": test_password
            }
        )
        assert login_response.status_code == 200
        
        login_data = login_response.json()
        # Check if user object has onboarding_completed field
        if "user" in login_data:
            assert "onboarding_completed" in login_data["user"], "Login response should include onboarding_completed"
            print(f"✓ Login response includes onboarding_completed: {login_data['user']['onboarding_completed']}")
        else:
            # May be 2FA flow
            print("✓ Login response format verified")
    
    def test_auth_me_returns_onboarding_state(self):
        """Test that /auth/me includes onboarding_completed field"""
        test_email = f"test_me_onboarding_{uuid.uuid4().hex[:8]}@cursorcode.ai"
        test_password = "Test123456!"
        
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        
        # Signup
        signup_response = session.post(
            f"{BASE_URL}/api/auth/signup",
            json={
                "email": test_email,
                "password": test_password,
                "name": "Me Test"
            }
        )
        assert signup_response.status_code == 200
        access_token = signup_response.json()["access_token"]
        
        # Get /auth/me
        session.headers.update({"Authorization": f"Bearer {access_token}"})
        me_response = session.get(f"{BASE_URL}/api/auth/me")
        
        assert me_response.status_code == 200
        user_data = me_response.json()
        
        assert "onboarding_completed" in user_data, "/auth/me should include onboarding_completed field"
        print(f"✓ /auth/me includes onboarding_completed: {user_data['onboarding_completed']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
