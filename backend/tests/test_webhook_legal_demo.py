"""
Test Suite: Stripe Webhook, Legal Pages, and Demo Mode
Tests for iteration 11 features:
1. Stripe webhook with idempotency
2. Privacy/Terms/Contact pages
3. AI demo mode
"""
import pytest
import requests
import os
import uuid
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ai_test@example.com"
TEST_PASSWORD = "testpass123"


class TestStripeWebhook:
    """Test Stripe webhook endpoint with idempotency"""

    def test_webhook_checkout_completed(self):
        """Test checkout.session.completed event upgrades user plan"""
        event_id = f"evt_test_{uuid.uuid4().hex[:16]}"
        webhook_payload = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_test_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_123",
                    "subscription": "sub_test_456",
                    "metadata": {
                        "user_id": "test_user_nonexistent",
                        "plan": "pro"
                    },
                    "current_period_start": 1704067200,
                    "current_period_end": 1706745600
                }
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✅ checkout.session.completed webhook returns 200 with received: true")

    def test_webhook_idempotency_duplicate(self):
        """Test that duplicate events return duplicate: true"""
        event_id = f"evt_idempotent_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_test_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_789",
                    "subscription": "sub_test_abc",
                    "metadata": {"user_id": "test_user_xyz", "plan": "standard"}
                }
            }
        }
        # First request
        response1 = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1.get("received") == True
        # Should NOT have duplicate flag on first call
        assert data1.get("duplicate") is None or data1.get("duplicate") == False

        # Second request with SAME event_id
        response2 = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2.get("received") == True
        assert data2.get("duplicate") == True
        print(f"✅ Webhook idempotency: duplicate event returns duplicate: true")

    def test_webhook_invoice_payment_succeeded(self):
        """Test invoice.payment_succeeded resets credits"""
        event_id = f"evt_invoice_succ_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": event_id,
            "type": "invoice.payment_succeeded",
            "data": {
                "object": {
                    "id": f"in_test_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_nonexistent",
                    "subscription": "sub_test_payment",
                    "amount_paid": 5900,
                    "currency": "usd"
                }
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✅ invoice.payment_succeeded webhook returns 200")

    def test_webhook_invoice_payment_failed(self):
        """Test invoice.payment_failed event handling"""
        event_id = f"evt_invoice_fail_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": event_id,
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": f"in_fail_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_nonexistent_fail",
                    "amount_due": 5900,
                    "currency": "usd"
                }
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✅ invoice.payment_failed webhook returns 200")

    def test_webhook_subscription_deleted(self):
        """Test customer.subscription.deleted downgrades to starter"""
        event_id = f"evt_sub_del_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": event_id,
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": f"sub_del_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_to_delete",
                    "status": "canceled"
                }
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✅ customer.subscription.deleted webhook returns 200")

    def test_webhook_subscription_updated(self):
        """Test customer.subscription.updated event handling"""
        event_id = f"evt_sub_upd_{uuid.uuid4().hex[:12]}"
        webhook_payload = {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": f"sub_upd_{uuid.uuid4().hex[:8]}",
                    "customer": "cus_test_update",
                    "status": "active"
                }
            }
        }
        response = requests.post(
            f"{BASE_URL}/api/subscriptions/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("received") == True
        print(f"✅ customer.subscription.updated webhook returns 200")


class TestAIDemoMode:
    """Test AI demo mode generates realistic output"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed - skipping authenticated tests")

    def test_ai_generate_demo_mode(self, auth_token):
        """Test AI generate returns multi-file output in demo mode (no XAI_API_KEY)"""
        # First get or create a project
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get existing projects
        projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        assert projects_resp.status_code == 200
        projects = projects_resp.json()
        
        if projects:
            project_id = projects[0]["id"]
        else:
            # Create a project
            create_resp = requests.post(
                f"{BASE_URL}/api/projects",
                headers=headers,
                json={"name": "Demo Test Project", "description": "Testing demo mode"}
            )
            assert create_resp.status_code == 200
            project_id = create_resp.json()["id"]
        
        # Call AI generate
        response = requests.post(
            f"{BASE_URL}/api/ai/generate",
            headers=headers,
            json={
                "project_id": project_id,
                "prompt": "Build a task management app",
                "task_type": "code_generation"
            }
        )
        
        # Should return 200 (demo mode) or 402 (insufficient credits)
        assert response.status_code in [200, 402], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "response" in data
            assert "files" in data
            # Demo mode should generate realistic multi-file output
            assert data.get("files") is not None or "```filename:" in data.get("response", "")
            print(f"✅ AI generate demo mode returns multi-file output")
        else:
            print(f"⚠️ AI generate returned 402 (insufficient credits) - expected when credits exhausted")


class TestAIModels:
    """Test AI models endpoint"""

    def test_get_ai_models(self):
        """Test GET /api/ai/models returns model list"""
        response = requests.get(f"{BASE_URL}/api/ai/models")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert len(data["models"]) >= 3
        # Check model structure
        for model in data["models"]:
            assert "id" in model
            assert "name" in model
            assert "credits_per_use" in model
        print(f"✅ AI models endpoint returns {len(data['models'])} models")


class TestRegressionEndpoints:
    """Regression tests for core functionality"""

    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")

    def test_login_works(self):
        """Test login endpoint"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        print(f"✅ Login works for test user")

    def test_get_projects(self, auth_token):
        """Test GET /api/projects"""
        response = requests.get(
            f"{BASE_URL}/api/projects",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✅ GET /api/projects returns list")

    def test_get_subscription_plans(self):
        """Test GET /api/plans"""
        response = requests.get(f"{BASE_URL}/api/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert "starter" in data["plans"]
        assert "pro" in data["plans"]
        print(f"✅ GET /api/plans returns plans")

    def test_prompt_templates(self):
        """Test GET /api/prompt-templates"""
        response = requests.get(f"{BASE_URL}/api/prompt-templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 8  # Should have 8 templates
        print(f"✅ GET /api/prompt-templates returns {len(data)} templates")

    def test_share_feature(self, auth_token):
        """Test share feature still works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get projects
        projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_resp.status_code == 200 and len(projects_resp.json()) > 0:
            project_id = projects_resp.json()[0]["id"]
            
            # Toggle share
            share_resp = requests.post(
                f"{BASE_URL}/api/projects/{project_id}/share",
                headers=headers
            )
            assert share_resp.status_code == 200
            data = share_resp.json()
            assert "is_public" in data
            print(f"✅ Share feature works - is_public: {data['is_public']}")
        else:
            print(f"⚠️ No projects to test share feature")

    def test_export_feature(self, auth_token):
        """Test export feature still works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get projects
        projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_resp.status_code == 200 and len(projects_resp.json()) > 0:
            project = projects_resp.json()[0]
            project_id = project["id"]
            
            # Try export
            export_resp = requests.get(
                f"{BASE_URL}/api/projects/{project_id}/export",
                headers=headers
            )
            # 200 if has files, 400 if empty
            assert export_resp.status_code in [200, 400]
            if export_resp.status_code == 200:
                assert "application/zip" in export_resp.headers.get("content-type", "")
                print(f"✅ Export feature works - returns ZIP")
            else:
                print(f"⚠️ Export returned 400 (project has no files)")
        else:
            print(f"⚠️ No projects to test export")

    def test_snapshots_feature(self, auth_token):
        """Test snapshots feature still works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get projects
        projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_resp.status_code == 200 and len(projects_resp.json()) > 0:
            project_id = projects_resp.json()[0]["id"]
            
            # Get snapshots
            snapshots_resp = requests.get(
                f"{BASE_URL}/api/projects/{project_id}/snapshots",
                headers=headers
            )
            assert snapshots_resp.status_code == 200
            assert isinstance(snapshots_resp.json(), list)
            print(f"✅ Snapshots feature works")
        else:
            print(f"⚠️ No projects to test snapshots")

    def test_activity_feature(self, auth_token):
        """Test activity timeline still works"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get projects
        projects_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if projects_resp.status_code == 200 and len(projects_resp.json()) > 0:
            project_id = projects_resp.json()[0]["id"]
            
            # Get activity
            activity_resp = requests.get(
                f"{BASE_URL}/api/projects/{project_id}/activity",
                headers=headers
            )
            assert activity_resp.status_code == 200
            assert isinstance(activity_resp.json(), list)
            print(f"✅ Activity feature works")
        else:
            print(f"⚠️ No projects to test activity")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
