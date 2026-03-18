"""
CursorCode AI API Tests
Tests all backend API endpoints for the CursorCode AI platform

Modules tested:
- Health & Root endpoints
- Authentication (login, signup, token refresh)
- User profile management
- Projects CRUD
- AI generation endpoints
- Subscription plans
- Deployment functionality
"""
import pytest
import requests
import os
import time

# Get backend URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://grok-devops.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "test@cursorcode.ai"
TEST_PASSWORD = "Test123456!"
TEST_NAME = "Test User"


class TestHealthAndRoot:
    """Health check and root endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        print("✓ Health endpoint working")
    
    def test_root_endpoint(self):
        """Test /api/ returns API info"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CursorCode AI API"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        print("✓ Root endpoint working")


class TestPlansAndModels:
    """Subscription plans and AI models tests"""
    
    def test_get_plans(self):
        """Test /api/plans returns all 5 subscription plans"""
        response = requests.get(f"{BASE_URL}/api/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        plans = data["plans"]
        
        # Verify all 5 plans exist
        expected_plans = ["starter", "standard", "pro", "premier", "ultra"]
        for plan_name in expected_plans:
            assert plan_name in plans, f"Missing plan: {plan_name}"
        
        # Verify plan data structure
        starter = plans["starter"]
        assert starter["name"] == "Starter"
        assert starter["price"] == 0
        assert starter["credits"] == 10
        assert "features" in starter
        
        pro = plans["pro"]
        assert pro["price"] == 59
        assert pro["credits"] == 150
        
        ultra = plans["ultra"]
        assert ultra["price"] == 499
        assert ultra["credits"] == 2000
        
        print("✓ Plans endpoint returns all 5 plans correctly")
    
    def test_get_ai_models(self):
        """Test /api/ai/models returns 3 AI models"""
        response = requests.get(f"{BASE_URL}/api/ai/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        models = data["models"]
        
        assert len(models) == 3, f"Expected 3 models, got {len(models)}"
        
        # Verify model IDs
        model_ids = [m["id"] for m in models]
        assert "grok-4-latest" in model_ids
        assert "grok-4-1-fast-reasoning" in model_ids
        assert "grok-4-1-fast-non-reasoning" in model_ids
        
        # Verify credits per use
        for model in models:
            assert "credits_per_use" in model
            assert model["credits_per_use"] in [1, 2, 3]
        
        print("✓ AI models endpoint returns 3 models correctly")


class TestAuthentication:
    """Authentication flow tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup for auth tests"""
        self.access_token = None
        self.refresh_token = None
        self.user = None
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if response.status_code == 401:
            print("⚠ Test user doesn't exist, creating...")
            # Try signup first
            signup_response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
            )
            if signup_response.status_code == 400:
                # User exists but wrong password
                pytest.skip("Test user exists with different password")
            assert signup_response.status_code == 200, f"Signup failed: {signup_response.text}"
            # Try login again
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
            )
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        
        print("✓ Login successful with token returned")
        return data
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        print("✓ Invalid credentials returns 401")
    
    def test_get_current_user(self):
        """Test GET /api/auth/me returns user info"""
        # First login
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code != 200:
            pytest.skip("Could not login to test /auth/me")
        
        token = login_response.json()["access_token"]
        
        # Get user info
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == TEST_EMAIL
        assert "id" in data
        assert "plan" in data
        assert "credits" in data
        print("✓ GET /auth/me returns user info")


class TestProjects:
    """Project CRUD tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for project tests"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            # Try signup
            response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
            )
        if response.status_code != 200:
            pytest.skip("Could not authenticate for project tests")
        return response.json()["access_token"]
    
    def test_create_project(self, auth_token):
        """Test creating a new project"""
        project_name = f"TEST_Project_{int(time.time())}"
        response = requests.post(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": project_name, "description": "Test project description"}
        )
        
        assert response.status_code == 200, f"Create project failed: {response.text}"
        data = response.json()
        assert data["name"] == project_name
        assert "id" in data
        assert data["status"] == "draft"
        
        print(f"✓ Created project: {project_name}")
        return data["id"]
    
    def test_list_projects(self, auth_token):
        """Test listing user projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Listed {len(data)} projects")
    
    def test_get_project(self, auth_token):
        """Test getting a specific project"""
        # First create a project
        project_name = f"TEST_GetProject_{int(time.time())}"
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": project_name}
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create project for get test")
        
        project_id = create_response.json()["id"]
        
        # Get the project
        response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["name"] == project_name
        print(f"✓ Got project by ID: {project_id}")
    
    def test_delete_project(self, auth_token):
        """Test deleting a project"""
        # Create a project to delete
        project_name = f"TEST_DeleteProject_{int(time.time())}"
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": project_name}
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create project for delete test")
        
        project_id = create_response.json()["id"]
        
        # Delete the project
        delete_response = requests.delete(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert delete_response.status_code == 200
        
        # Verify it's deleted
        get_response = requests.get(
            f"{BASE_URL}/api/projects/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 404
        print(f"✓ Deleted project and verified removal")


class TestAIGeneration:
    """AI generation endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
            )
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        return response.json()["access_token"]
    
    def test_ai_build_demo_response(self, auth_token):
        """Test /api/ai/build returns demo response when no XAI_API_KEY"""
        response = requests.post(
            f"{BASE_URL}/api/ai/build",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"prompt": "Build a simple todo app"}
        )
        
        assert response.status_code == 200, f"AI build failed: {response.text}"
        data = response.json()
        
        # Should return demo response since XAI_API_KEY is not configured
        assert data.get("demo") == True or "demo" in str(data.get("architecture", "")).lower()
        print("✓ AI build returns demo response (no XAI_API_KEY configured)")


class TestSubscriptions:
    """Subscription endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
            )
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        return response.json()["access_token"]
    
    def test_get_current_subscription(self, auth_token):
        """Test /api/subscriptions/current returns user subscription info"""
        response = requests.get(
            f"{BASE_URL}/api/subscriptions/current",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200, f"Get subscription failed: {response.text}"
        data = response.json()
        
        assert "plan" in data
        assert "credits" in data
        assert "credits_used" in data
        assert "credits_remaining" in data
        assert "plan_details" in data
        
        print(f"✓ Current subscription: {data['plan']} plan, {data['credits_remaining']} credits remaining")
    
    def test_create_checkout_demo_mode(self, auth_token):
        """Test Stripe checkout creation returns demo URL when no Stripe key"""
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/create-checkout",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"plan": "pro"}
        )
        
        assert response.status_code == 200, f"Checkout failed: {response.text}"
        data = response.json()
        
        # Should return demo response since Stripe is not configured
        assert "url" in data
        assert data.get("demo") == True or "demo" in data.get("url", "")
        print("✓ Stripe checkout returns demo URL (no Stripe key configured)")


class TestDeployment:
    """Deployment endpoint tests"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            response = requests.post(
                f"{BASE_URL}/api/auth/signup",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD, "name": TEST_NAME}
            )
        if response.status_code != 200:
            pytest.skip("Could not authenticate")
        return response.json()["access_token"]
    
    def test_deploy_project(self, auth_token):
        """Test deploying a project creates deployment record"""
        # First create a project
        project_name = f"TEST_DeployProject_{int(time.time())}"
        create_response = requests.post(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"name": project_name}
        )
        
        if create_response.status_code != 200:
            pytest.skip("Could not create project for deployment test")
        
        project_id = create_response.json()["id"]
        
        # Deploy the project
        deploy_response = requests.post(
            f"{BASE_URL}/api/deploy/{project_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert deploy_response.status_code == 200, f"Deploy failed: {deploy_response.text}"
        data = deploy_response.json()
        
        assert "deployment_id" in data
        assert "deployed_url" in data
        assert "cursorcode.app" in data["deployed_url"]
        assert data["status"] == "deployed"
        
        print(f"✓ Deployed project to: {data['deployed_url']}")
    
    def test_list_deployments(self, auth_token):
        """Test listing user deployments"""
        response = requests.get(
            f"{BASE_URL}/api/deployments",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "deployments" in data
        print(f"✓ Listed {len(data['deployments'])} deployments")


# Cleanup fixture
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_projects():
    """Cleanup TEST_ prefixed projects after all tests"""
    yield
    # Cleanup
    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            # Get projects
            projects_response = requests.get(
                f"{BASE_URL}/api/projects",
                headers={"Authorization": f"Bearer {token}"}
            )
            if projects_response.status_code == 200:
                projects = projects_response.json()
                for project in projects:
                    if project["name"].startswith("TEST_"):
                        requests.delete(
                            f"{BASE_URL}/api/projects/{project['id']}",
                            headers={"Authorization": f"Bearer {token}"}
                        )
                print(f"Cleaned up test projects")
    except Exception as e:
        print(f"Cleanup error: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
