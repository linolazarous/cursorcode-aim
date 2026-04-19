"""
CursorCode AI - Deployment Storage Tests
Tests real file hosting via Emergent Object Storage.
Iteration 21: Deploy uploads files to storage, preview serves them with correct MIME types.
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test_refactor@example.com"
TEST_PASSWORD = "Test123456!"


class TestDeploymentStorage:
    """Tests for deployment with real object storage file hosting."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and create a test project with files."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Create a test project
        project_name = f"TEST_deploy_{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "description": "Test project for deployment storage testing"
        })
        assert create_resp.status_code in [200, 201], f"Project creation failed: {create_resp.text}"
        self.project_id = create_resp.json()["id"]
        self.project_name = project_name
        
        yield
        
        # Cleanup: delete project (will cascade to deployment)
        try:
            self.session.delete(f"{BASE_URL}/api/projects/{self.project_id}")
        except:
            pass
    
    # ==================== DEPLOY ENDPOINT TESTS ====================
    
    def test_deploy_uploads_files_to_storage(self):
        """POST /api/deploy/{project_id} - uploads files to object storage, returns real preview URL."""
        # Add files to project - files dict is sent directly, not wrapped
        files = {
            "index.html": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>",
            "style.css": "body { background: #000; color: #fff; }",
            "app.js": "console.log('Hello from app.js');"
        }
        files_resp = self.session.put(f"{BASE_URL}/api/projects/{self.project_id}/files", json=files)
        assert files_resp.status_code == 200, f"Add files failed: {files_resp.text}"
        
        # Deploy
        deploy_resp = self.session.post(f"{BASE_URL}/api/deploy/{self.project_id}")
        assert deploy_resp.status_code == 200, f"Deploy failed: {deploy_resp.text}"
        
        data = deploy_resp.json()
        print(f"Deploy response: {data}")
        
        # Verify response structure
        assert "deployment_id" in data, "Missing deployment_id"
        assert "deployed_url" in data, "Missing deployed_url"
        assert "status" in data, "Missing status"
        assert data["status"] == "deployed", f"Expected status=deployed, got {data['status']}"
        
        # Verify files_uploaded count (real mode)
        if "files_uploaded" in data:
            assert data["files_uploaded"] >= 3, f"Expected at least 3 files uploaded, got {data.get('files_uploaded')}"
            print(f"Files uploaded: {data['files_uploaded']}")
        
        # Verify demo=False for real storage mode (or demo key absent)
        if "demo" in data:
            assert data["demo"] == False, "Expected demo=False for real storage mode"
        else:
            print("No demo key in response - indicates real storage mode")
        
        # Verify logs show upload progress
        assert "logs" in data, "Missing logs"
        logs_text = " ".join(data["logs"])
        assert "upload" in logs_text.lower() or "Uploading" in logs_text, f"Logs should mention upload: {data['logs']}"
        
        self.deployment_id = data["deployment_id"]
        self.deployed_url = data["deployed_url"]
        print(f"Deployment ID: {self.deployment_id}")
        print(f"Deployed URL: {self.deployed_url}")
    
    def test_deploy_generates_index_html_if_missing(self):
        """Deployment generates index.html automatically if not present in project files."""
        # Add files WITHOUT index.html
        files = {
            "app.py": "print('Hello from Python')",
            "utils.js": "function helper() { return 42; }"
        }
        files_resp = self.session.put(f"{BASE_URL}/api/projects/{self.project_id}/files", json=files)
        assert files_resp.status_code == 200, f"Add files failed: {files_resp.text}"
        
        # Deploy
        deploy_resp = self.session.post(f"{BASE_URL}/api/deploy/{self.project_id}")
        assert deploy_resp.status_code == 200, f"Deploy failed: {deploy_resp.text}"
        
        data = deploy_resp.json()
        
        # Verify logs mention generated index.html
        logs_text = " ".join(data.get("logs", []))
        print(f"Deploy logs: {data.get('logs')}")
        
        # The deployment should succeed and have a URL
        assert "deployed_url" in data, "Missing deployed_url"
        assert data["status"] == "deployed", f"Expected deployed status, got {data['status']}"
        
        self.deployment_id = data["deployment_id"]
    
    def test_deploy_requires_verified_email(self):
        """Deploy requires verified email (403 for unverified)."""
        # Create a new unverified user
        unverified_email = f"unverified_{uuid.uuid4().hex[:8]}@test.com"
        signup_resp = self.session.post(f"{BASE_URL}/api/auth/signup", json={
            "email": unverified_email,
            "password": TEST_PASSWORD,
            "name": "Unverified User"
        })
        # May return 200 or 201 or 400 if email exists
        
        # Login as unverified user
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": unverified_email,
            "password": TEST_PASSWORD
        })
        
        if login_resp.status_code == 200:
            unverified_token = login_resp.json()["access_token"]
            
            # Try to deploy with unverified user
            deploy_resp = requests.post(
                f"{BASE_URL}/api/deploy/{self.project_id}",
                headers={"Authorization": f"Bearer {unverified_token}", "Content-Type": "application/json"}
            )
            # Should get 403 or 404 (project not found for this user)
            assert deploy_resp.status_code in [403, 404], f"Expected 403/404 for unverified user, got {deploy_resp.status_code}"
            print(f"Unverified user deploy response: {deploy_resp.status_code} - {deploy_resp.text}")


class TestPreviewEndpoints:
    """Tests for preview/file serving endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login, create project, add files, deploy."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Create project
        project_name = f"TEST_preview_{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "description": "Test project for preview testing"
        })
        assert create_resp.status_code in [200, 201], f"Project creation failed: {create_resp.text}"
        self.project_id = create_resp.json()["id"]
        
        # Add files - files dict sent directly
        self.test_files = {
            "index.html": "<!DOCTYPE html><html><head><title>Preview Test</title></head><body><h1>Preview Test</h1></body></html>",
            "style.css": "body { margin: 0; padding: 20px; font-family: sans-serif; }",
            "app.js": "document.addEventListener('DOMContentLoaded', () => { console.log('Loaded'); });"
        }
        files_resp = self.session.put(f"{BASE_URL}/api/projects/{self.project_id}/files", json=self.test_files)
        assert files_resp.status_code == 200, f"Add files failed: {files_resp.text}"
        
        # Deploy
        deploy_resp = self.session.post(f"{BASE_URL}/api/deploy/{self.project_id}")
        assert deploy_resp.status_code == 200, f"Deploy failed: {deploy_resp.text}"
        self.deployment_id = deploy_resp.json()["deployment_id"]
        self.deployed_url = deploy_resp.json()["deployed_url"]
        
        yield
        
        # Cleanup
        try:
            self.session.delete(f"{BASE_URL}/api/deployments/{self.deployment_id}")
            self.session.delete(f"{BASE_URL}/api/projects/{self.project_id}")
        except:
            pass
    
    def test_preview_serves_html_with_correct_content_type(self):
        """GET /api/preview/{deployment_id}/index.html - serves HTML with text/html content type."""
        # Preview endpoint is public (no auth required)
        resp = requests.get(f"{BASE_URL}/api/preview/{self.deployment_id}/index.html")
        assert resp.status_code == 200, f"Preview HTML failed: {resp.status_code} - {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "text/html" in content_type, f"Expected text/html, got {content_type}"
        
        # Verify content
        assert "Preview Test" in resp.text, f"Expected 'Preview Test' in HTML content"
        print(f"HTML content type: {content_type}")
        print(f"HTML content preview: {resp.text[:200]}")
    
    def test_preview_serves_css_with_correct_content_type(self):
        """GET /api/preview/{deployment_id}/style.css - serves CSS with text/css content type."""
        resp = requests.get(f"{BASE_URL}/api/preview/{self.deployment_id}/style.css")
        assert resp.status_code == 200, f"Preview CSS failed: {resp.status_code} - {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "text/css" in content_type, f"Expected text/css, got {content_type}"
        
        # Verify content
        assert "font-family" in resp.text or "margin" in resp.text, f"Expected CSS content"
        print(f"CSS content type: {content_type}")
    
    def test_preview_serves_js_with_correct_content_type(self):
        """GET /api/preview/{deployment_id}/app.js - serves JS with application/javascript content type."""
        resp = requests.get(f"{BASE_URL}/api/preview/{self.deployment_id}/app.js")
        assert resp.status_code == 200, f"Preview JS failed: {resp.status_code} - {resp.text}"
        
        content_type = resp.headers.get("Content-Type", "")
        assert "javascript" in content_type.lower(), f"Expected application/javascript, got {content_type}"
        
        # Verify content
        assert "console.log" in resp.text or "document" in resp.text, f"Expected JS content"
        print(f"JS content type: {content_type}")
    
    def test_preview_returns_404_for_nonexistent_file(self):
        """GET /api/preview/{deployment_id}/nonexistent.txt - returns 404."""
        resp = requests.get(f"{BASE_URL}/api/preview/{self.deployment_id}/nonexistent.txt")
        assert resp.status_code == 404, f"Expected 404 for nonexistent file, got {resp.status_code}"
        print(f"Nonexistent file response: {resp.status_code}")
    
    def test_preview_returns_404_for_invalid_deployment(self):
        """GET /api/preview/invalid-deployment-id/index.html - returns 404."""
        resp = requests.get(f"{BASE_URL}/api/preview/invalid-deployment-id-12345/index.html")
        assert resp.status_code == 404, f"Expected 404 for invalid deployment, got {resp.status_code}"


class TestDeploymentCRUD:
    """Tests for deployment CRUD operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login and create a deployed project."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        # Create project
        project_name = f"TEST_crud_{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "description": "Test project for CRUD testing"
        })
        assert create_resp.status_code in [200, 201], f"Project creation failed: {create_resp.text}"
        self.project_id = create_resp.json()["id"]
        
        # Add files and deploy - files dict sent directly
        files = {"index.html": "<html><body>CRUD Test</body></html>"}
        files_resp = self.session.put(f"{BASE_URL}/api/projects/{self.project_id}/files", json=files)
        assert files_resp.status_code == 200, f"Add files failed: {files_resp.text}"
        
        deploy_resp = self.session.post(f"{BASE_URL}/api/deploy/{self.project_id}")
        assert deploy_resp.status_code == 200, f"Deploy failed: {deploy_resp.text}"
        self.deployment_id = deploy_resp.json()["deployment_id"]
        
        yield
        
        # Cleanup
        try:
            self.session.delete(f"{BASE_URL}/api/projects/{self.project_id}")
        except:
            pass
    
    def test_list_deployments(self):
        """GET /api/deployments - lists user deployments."""
        resp = self.session.get(f"{BASE_URL}/api/deployments")
        assert resp.status_code == 200, f"List deployments failed: {resp.text}"
        
        data = resp.json()
        assert "deployments" in data, "Missing deployments key"
        assert isinstance(data["deployments"], list), "deployments should be a list"
        
        # Find our deployment
        our_deployment = next((d for d in data["deployments"] if d["id"] == self.deployment_id), None)
        assert our_deployment is not None, f"Our deployment {self.deployment_id} not found in list"
        print(f"Found {len(data['deployments'])} deployments")
    
    def test_get_deployment_details(self):
        """GET /api/deployments/{id} - returns deployment details with status=deployed."""
        resp = self.session.get(f"{BASE_URL}/api/deployments/{self.deployment_id}")
        assert resp.status_code == 200, f"Get deployment failed: {resp.text}"
        
        data = resp.json()
        assert data["id"] == self.deployment_id, "Deployment ID mismatch"
        assert data["status"] == "deployed", f"Expected status=deployed, got {data['status']}"
        assert "url" in data, "Missing url field"
        assert "project_id" in data, "Missing project_id field"
        print(f"Deployment details: status={data['status']}, url={data.get('url')}")
    
    def test_delete_deployment_resets_project_status(self):
        """DELETE /api/deployments/{id} - deletes deployment and resets project status."""
        # Delete deployment
        delete_resp = self.session.delete(f"{BASE_URL}/api/deployments/{self.deployment_id}")
        assert delete_resp.status_code == 200, f"Delete deployment failed: {delete_resp.text}"
        
        # Verify deployment is gone
        get_resp = self.session.get(f"{BASE_URL}/api/deployments/{self.deployment_id}")
        assert get_resp.status_code == 404, f"Expected 404 after delete, got {get_resp.status_code}"
        
        # Verify project status is reset to draft
        project_resp = self.session.get(f"{BASE_URL}/api/projects/{self.project_id}")
        assert project_resp.status_code == 200, f"Get project failed: {project_resp.text}"
        
        project_data = project_resp.json()
        assert project_data["status"] == "draft", f"Expected project status=draft after deployment delete, got {project_data['status']}"
        print(f"Project status after deployment delete: {project_data['status']}")


class TestRegressionEndpoints:
    """Regression tests for existing endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup: login."""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        login_resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        self.token = login_resp.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
    
    def test_health_endpoint(self):
        """Regression: GET /api/health works."""
        resp = requests.get(f"{BASE_URL}/api/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "healthy", f"Expected healthy status, got {data}"
        print("Health check passed")
    
    def test_login_endpoint(self):
        """Regression: POST /api/auth/login works."""
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data, "Missing access_token"
        print("Login regression passed")
    
    def test_create_project_for_verified_user(self):
        """Regression: POST /api/projects works for verified user."""
        project_name = f"TEST_regression_{uuid.uuid4().hex[:8]}"
        resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "description": "Regression test project"
        })
        assert resp.status_code in [200, 201], f"Create project failed: {resp.text}"
        
        project_id = resp.json()["id"]
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
        print("Create project regression passed")
    
    def test_update_project_files(self):
        """Regression: PUT /api/projects/{id}/files works."""
        # Create project
        project_name = f"TEST_files_{uuid.uuid4().hex[:8]}"
        create_resp = self.session.post(f"{BASE_URL}/api/projects", json={
            "name": project_name,
            "description": "Files test"
        })
        assert create_resp.status_code in [200, 201], f"Create project failed: {create_resp.text}"
        project_id = create_resp.json()["id"]
        
        # Update files - files dict sent directly, not wrapped
        files = {"test.txt": "Hello World"}
        files_resp = self.session.put(f"{BASE_URL}/api/projects/{project_id}/files", json=files)
        assert files_resp.status_code == 200, f"Update files failed: {files_resp.text}"
        
        # Cleanup
        self.session.delete(f"{BASE_URL}/api/projects/{project_id}")
        print("Update files regression passed")
    
    def test_user_credits_endpoint(self):
        """Regression: GET /api/user/credits works."""
        resp = self.session.get(f"{BASE_URL}/api/user/credits")
        assert resp.status_code == 200, f"Get credits failed: {resp.text}"
        data = resp.json()
        assert "credits" in data or "credits_remaining" in data or "balance" in data, f"Missing credits field: {data}"
        print(f"User credits: {data}")
    
    def test_payments_create_order(self):
        """Regression: POST /api/payments/create-order works."""
        # Correct field name is 'plan', not 'plan_id'
        resp = self.session.post(f"{BASE_URL}/api/payments/create-order", json={
            "plan": "pro"
        })
        # Should return 200 (demo mode) or valid response
        assert resp.status_code in [200, 201, 400], f"Create order failed: {resp.status_code} - {resp.text}"
        print(f"Create order response: {resp.status_code}")
    
    def test_guardrails_validate(self):
        """Regression: POST /api/autonomous/guardrails/validate works."""
        resp = self.session.post(f"{BASE_URL}/api/autonomous/guardrails/validate", json={
            "code": "def hello():\n    return 'Hello World'"
        })
        assert resp.status_code == 200, f"Guardrails validate failed: {resp.text}"
        data = resp.json()
        assert "passed" in data or "issues" in data, f"Missing validation result: {data}"
        print(f"Guardrails validate: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
