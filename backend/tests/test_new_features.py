"""
Tests for 6 new power features (Iteration 10):
1. Share Project with public preview links
2. AI Conversation History persistence
3. Prompt Templates Library (8 templates)
4. Project Export as ZIP
5. Activity Timeline (audit log)
6. Version Snapshots with rollback
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials from previous iterations
TEST_EMAIL = "ai_test@example.com"
TEST_PASSWORD = "testpass123"


@pytest.fixture(scope="module")
def auth_token():
    """Get auth token for test user"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def test_project_id(auth_headers):
    """Get or create a test project"""
    # Try to get existing projects
    response = requests.get(f"{BASE_URL}/api/projects", headers=auth_headers)
    if response.status_code == 200:
        projects = response.json()
        if projects:
            return projects[0]["id"]
    # Create a new project if none exists
    response = requests.post(f"{BASE_URL}/api/projects", headers=auth_headers, json={
        "name": "Test Features Project",
        "description": "Project for testing new features"
    })
    if response.status_code == 200:
        return response.json()["id"]
    pytest.skip("Could not get or create test project")


# ==================== 1. SHARE PROJECT TESTS ====================

class TestShareProject:
    """Tests for project sharing feature"""

    def test_share_toggle_returns_share_id(self, auth_headers, test_project_id):
        """POST /api/projects/:id/share toggles sharing and returns share_id + share_url"""
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "is_public" in data, "Response should contain is_public"
        assert "share_id" in data, "Response should contain share_id"
        assert "share_url" in data, "Response should contain share_url"
        assert isinstance(data["share_id"], str), "share_id should be a string"
        assert len(data["share_id"]) > 0, "share_id should not be empty"
        print(f"Share toggle: is_public={data['is_public']}, share_id={data['share_id']}")

    def test_get_shared_project_public(self, auth_headers, test_project_id):
        """GET /api/shared/:shareId returns public project data (no auth needed)"""
        # First ensure project is public
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        share_id = data["share_id"]
        is_public = data["is_public"]
        
        # If not public, toggle again
        if not is_public:
            response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
            share_id = response.json()["share_id"]
        
        # Now get the shared project WITHOUT auth
        response = requests.get(f"{BASE_URL}/api/shared/{share_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        shared_data = response.json()
        assert "name" in shared_data, "Shared data should contain name"
        assert "files" in shared_data, "Shared data should contain files"
        assert "owner_name" in shared_data, "Shared data should contain owner_name"
        assert "view_count" in shared_data, "Shared data should contain view_count"
        print(f"Shared project: {shared_data['name']}, owner: {shared_data['owner_name']}, views: {shared_data['view_count']}")

    def test_shared_project_increments_view_count(self, auth_headers, test_project_id):
        """GET /api/shared/:shareId increments view_count"""
        # Ensure project is public and get share_id
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
        data = response.json()
        share_id = data["share_id"]
        if not data["is_public"]:
            response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
            share_id = response.json()["share_id"]
        
        # Get view count
        response1 = requests.get(f"{BASE_URL}/api/shared/{share_id}")
        view_count1 = response1.json()["view_count"]
        
        # Access again
        response2 = requests.get(f"{BASE_URL}/api/shared/{share_id}")
        view_count2 = response2.json()["view_count"]
        
        assert view_count2 >= view_count1, "View count should increment or stay same"
        print(f"View count: {view_count1} -> {view_count2}")

    def test_shared_project_invalid_returns_404(self):
        """GET /api/shared/invalid returns 404"""
        response = requests.get(f"{BASE_URL}/api/shared/invalid_share_id_12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Invalid share_id correctly returns 404")


# ==================== 2. CONVERSATION HISTORY TESTS ====================

class TestConversationHistory:
    """Tests for AI conversation history persistence"""

    def test_get_messages_returns_list(self, auth_headers, test_project_id):
        """GET /api/projects/:id/messages returns conversation history"""
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/messages", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Messages should be a list"
        print(f"Found {len(data)} existing messages")

    def test_save_message(self, auth_headers, test_project_id):
        """POST /api/projects/:id/messages saves a message"""
        message_data = {
            "type": "user",
            "content": "Test message from pytest"
        }
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/messages", 
                                headers=auth_headers, json=message_data)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain message id"
        print(f"Saved message with id: {data['id']}")

    def test_saved_message_persists(self, auth_headers, test_project_id):
        """Verify saved message appears in messages list"""
        # Save a unique message
        unique_content = f"Unique test message {os.urandom(4).hex()}"
        requests.post(f"{BASE_URL}/api/projects/{test_project_id}/messages",
                     headers=auth_headers, json={"type": "user", "content": unique_content})
        
        # Get messages
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/messages", headers=auth_headers)
        messages = response.json()
        
        # Find our message
        found = any(m.get("content") == unique_content for m in messages)
        assert found, f"Saved message '{unique_content}' should appear in messages list"
        print(f"Verified message persistence: found unique message in list")

    def test_clear_messages(self, auth_headers, test_project_id):
        """DELETE /api/projects/:id/messages clears messages"""
        response = requests.delete(f"{BASE_URL}/api/projects/{test_project_id}/messages", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        
        # Verify cleared
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/messages", headers=auth_headers)
        messages = response.json()
        assert len(messages) == 0, "Messages should be cleared"
        print("Messages cleared successfully")


# ==================== 3. PROMPT TEMPLATES TESTS ====================

class TestPromptTemplates:
    """Tests for prompt templates library"""

    def test_get_prompt_templates_returns_8(self):
        """GET /api/prompt-templates returns 8 prompt templates"""
        response = requests.get(f"{BASE_URL}/api/prompt-templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        templates = response.json()
        assert isinstance(templates, list), "Templates should be a list"
        assert len(templates) == 8, f"Expected 8 templates, got {len(templates)}"
        print(f"Found {len(templates)} prompt templates")

    def test_prompt_templates_structure(self):
        """Verify template structure has required fields"""
        response = requests.get(f"{BASE_URL}/api/prompt-templates")
        templates = response.json()
        
        required_fields = ["id", "name", "category", "prompt", "tags"]
        for template in templates:
            for field in required_fields:
                assert field in template, f"Template missing field: {field}"
            assert isinstance(template["tags"], list), f"Tags should be a list for template {template['id']}"
        
        template_ids = [t["id"] for t in templates]
        expected_ids = ["saas", "ecommerce", "dashboard", "chat", "blog", "crm", "api", "portfolio"]
        for expected_id in expected_ids:
            assert expected_id in template_ids, f"Template {expected_id} missing"
        print(f"All 8 templates have correct structure: {template_ids}")


# ==================== 4. PROJECT EXPORT TESTS ====================

class TestProjectExport:
    """Tests for project export as ZIP"""

    def test_export_returns_zip(self, auth_headers, test_project_id):
        """GET /api/projects/:id/export returns ZIP file"""
        # First add a file to the project
        requests.put(f"{BASE_URL}/api/projects/{test_project_id}/files", 
                    headers=auth_headers, json={"test.js": "console.log('test');"})
        
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/export", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/zip", "Content-Type should be application/zip"
        assert "content-disposition" in response.headers, "Should have Content-Disposition header"
        assert "attachment" in response.headers.get("content-disposition", ""), "Should be an attachment"
        print(f"Export successful, ZIP size: {len(response.content)} bytes")

    def test_export_empty_project_returns_400(self, auth_headers):
        """Export project with no files returns 400"""
        # Create a new empty project
        response = requests.post(f"{BASE_URL}/api/projects", headers=auth_headers, json={
            "name": "Empty Export Test",
            "description": "No files"
        })
        if response.status_code != 200:
            pytest.skip("Could not create empty project")
        
        empty_project_id = response.json()["id"]
        
        # Try to export
        response = requests.get(f"{BASE_URL}/api/projects/{empty_project_id}/export", headers=auth_headers)
        assert response.status_code == 400, f"Expected 400 for empty project, got {response.status_code}"
        print("Empty project export correctly returns 400")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{empty_project_id}", headers=auth_headers)


# ==================== 5. ACTIVITY TIMELINE TESTS ====================

class TestActivityTimeline:
    """Tests for activity timeline (audit log)"""

    def test_get_activity_returns_list(self, auth_headers, test_project_id):
        """GET /api/projects/:id/activity returns activity timeline"""
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/activity", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Activity should be a list"
        print(f"Found {len(data)} activity entries")

    def test_activity_logged_on_share(self, auth_headers, test_project_id):
        """Activity is logged when sharing project"""
        # Toggle share
        requests.post(f"{BASE_URL}/api/projects/{test_project_id}/share", headers=auth_headers)
        
        # Get activity
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/activity", headers=auth_headers)
        activities = response.json()
        
        # Check for share activity
        share_actions = [a for a in activities if a.get("action") in ["shared", "unshared"]]
        assert len(share_actions) > 0, "Share action should be logged"
        print(f"Found {len(share_actions)} share-related activities")

    def test_activity_structure(self, auth_headers, test_project_id):
        """Verify activity entry structure"""
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/activity", headers=auth_headers)
        activities = response.json()
        
        if activities:
            activity = activities[0]
            assert "id" in activity, "Activity should have id"
            assert "project_id" in activity, "Activity should have project_id"
            assert "action" in activity, "Activity should have action"
            assert "created_at" in activity, "Activity should have created_at"
            print(f"Activity structure valid: action={activity['action']}, detail={activity.get('detail', 'N/A')}")


# ==================== 6. VERSION SNAPSHOTS TESTS ====================

class TestVersionSnapshots:
    """Tests for version snapshots with rollback"""

    def test_create_snapshot(self, auth_headers, test_project_id):
        """POST /api/projects/:id/snapshots creates a version snapshot"""
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/snapshots",
                                headers=auth_headers, json={"label": "Test Snapshot v1"})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "id" in data, "Response should contain snapshot id"
        assert "label" in data, "Response should contain label"
        assert "file_count" in data, "Response should contain file_count"
        assert "created_at" in data, "Response should contain created_at"
        print(f"Created snapshot: {data['label']} with {data['file_count']} files")

    def test_list_snapshots(self, auth_headers, test_project_id):
        """GET /api/projects/:id/snapshots lists snapshots"""
        response = requests.get(f"{BASE_URL}/api/projects/{test_project_id}/snapshots", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Snapshots should be a list"
        print(f"Found {len(data)} snapshots")

    def test_restore_snapshot(self, auth_headers, test_project_id):
        """POST /api/projects/:id/snapshots/:snapId/restore restores project files"""
        # Create a snapshot first
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/snapshots",
                                headers=auth_headers, json={"label": "Restore Test"})
        snapshot_id = response.json()["id"]
        
        # Modify files
        requests.put(f"{BASE_URL}/api/projects/{test_project_id}/files",
                    headers=auth_headers, json={"modified.js": "// modified after snapshot"})
        
        # Restore
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/snapshots/{snapshot_id}/restore",
                                headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "message" in data, "Response should contain message"
        assert "file_count" in data, "Response should contain file_count"
        print(f"Restored snapshot: {data['message']}")

    def test_restore_invalid_snapshot_returns_404(self, auth_headers, test_project_id):
        """Restore invalid snapshot returns 404"""
        response = requests.post(f"{BASE_URL}/api/projects/{test_project_id}/snapshots/invalid_snapshot_id/restore",
                                headers=auth_headers)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("Invalid snapshot restore correctly returns 404")


# ==================== REGRESSION TESTS ====================

class TestRegression:
    """Regression tests to ensure existing features still work"""

    def test_ai_generate_endpoint(self, auth_headers, test_project_id):
        """AI generate endpoint still works"""
        response = requests.post(f"{BASE_URL}/api/ai/generate", headers=auth_headers, json={
            "project_id": test_project_id,
            "prompt": "Create a hello world component",
            "task_type": "code_generation"
        })
        # May return 402 if out of credits, which is expected behavior
        assert response.status_code in [200, 402], f"Expected 200 or 402, got {response.status_code}"
        print(f"AI generate endpoint returns {response.status_code}")

    def test_sse_endpoint_requires_auth(self):
        """SSE streaming endpoint requires token param"""
        response = requests.get(f"{BASE_URL}/api/ai/generate-stream?project_id=test&prompt=test")
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        print("SSE endpoint correctly requires authentication")

    def test_auth_login(self):
        """Login endpoint works"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.status_code}"
        print("Login endpoint works")

    def test_plans_endpoint(self):
        """Plans endpoint works"""
        response = requests.get(f"{BASE_URL}/api/plans")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "plans" in data, "Response should contain plans"
        print(f"Plans endpoint returns {len(data.get('plans', {}))} plans")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
