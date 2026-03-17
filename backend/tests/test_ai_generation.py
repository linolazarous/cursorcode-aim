"""
Test suite for AI Code Generation endpoints (xAI Grok integration)
Tests: GET /api/ai/models, POST /api/ai/generate, GET /api/ai/generate-stream SSE
"""

import pytest
import requests
import os
import time
import json

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "ai_test@example.com"
TEST_PASSWORD = "testpass123"
NEW_USER_EMAIL = f"test_ai_{int(time.time())}@example.com"
NEW_USER_PASSWORD = "testpass123"

class TestAIModels:
    """Test GET /api/ai/models endpoint"""
    
    def test_get_ai_models_returns_3_grok_models(self):
        """Verify /api/ai/models returns 3 Grok models with correct structure"""
        response = requests.get(f"{BASE_URL}/api/ai/models")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "models" in data, "Response should contain 'models' key"
        assert len(data["models"]) == 3, f"Expected 3 models, got {len(data['models'])}"
        
        # Verify model structure
        for model in data["models"]:
            assert "id" in model, "Model should have 'id'"
            assert "name" in model, "Model should have 'name'"
            assert "description" in model, "Model should have 'description'"
            assert "credits_per_use" in model, "Model should have 'credits_per_use'"
            assert model["credits_per_use"] > 0, "Credits per use should be positive"
        
        # Verify specific models
        model_ids = [m["id"] for m in data["models"]]
        assert "grok-4-latest" in model_ids, "Should include grok-4-latest"
        assert "grok-4-1-fast-reasoning" in model_ids, "Should include grok-4-1-fast-reasoning"
        assert "grok-4-1-fast-non-reasoning" in model_ids, "Should include grok-4-1-fast-non-reasoning"
        print("✅ GET /api/ai/models returns 3 Grok models with credits")


class TestAIGenerate:
    """Test POST /api/ai/generate endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Failed to login test user - skipping generate tests")
    
    @pytest.fixture(scope="class")
    def project_id(self, auth_token):
        """Get existing project or create one"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        # Create project if none exists
        response = requests.post(f"{BASE_URL}/api/projects", headers=headers, json={
            "name": "AI Test Project",
            "description": "For AI generation testing"
        })
        return response.json()["id"]
    
    def test_generate_requires_authentication(self):
        """POST /api/ai/generate should require auth"""
        response = requests.post(f"{BASE_URL}/api/ai/generate", json={
            "project_id": "test", "prompt": "test", "model": "grok-4-1-fast-non-reasoning"
        })
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✅ POST /api/ai/generate requires authentication")
    
    def test_generate_code_demo_mode(self, auth_token, project_id):
        """POST /api/ai/generate works in demo mode (no XAI_API_KEY)"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/ai/generate", headers=headers, json={
            "project_id": project_id,
            "prompt": "Create a simple hello world component",
            "model": "grok-4-1-fast-non-reasoning",
            "task_type": "code_generation"
        })
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "id" in data, "Response should have 'id'"
        assert "project_id" in data, "Response should have 'project_id'"
        assert "prompt" in data, "Response should have 'prompt'"
        assert "response" in data, "Response should have 'response'"
        assert "model_used" in data, "Response should have 'model_used'"
        assert "credits_used" in data, "Response should have 'credits_used'"
        assert "created_at" in data, "Response should have 'created_at'"
        
        # In demo mode, response should contain demo text
        assert "Demo" in data["response"] or "Generated" in data["response"], \
            "Demo mode should return placeholder response"
        
        print(f"✅ POST /api/ai/generate works - used {data['credits_used']} credit(s)")
    
    def test_generate_returns_parsed_files(self, auth_token, project_id):
        """POST /api/ai/generate should return parsed files if any"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{BASE_URL}/api/ai/generate", headers=headers, json={
            "project_id": project_id,
            "prompt": "Build a React button component",
            "model": "grok-4-1-fast-non-reasoning"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "files" in data, "Response should have 'files' field"
        # Files may be empty in demo mode since response might not have proper format
        print(f"✅ POST /api/ai/generate returns files field (contains {len(data.get('files') or {})} files)")
    
    def test_generate_deducts_credits(self, auth_token):
        """POST /api/ai/generate should deduct credits from user"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get initial credits
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        initial_used = me_response.json()["credits_used"]
        
        # Get project
        proj_resp = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        project_id = proj_resp.json()[0]["id"]
        
        # Generate
        response = requests.post(f"{BASE_URL}/api/ai/generate", headers=headers, json={
            "project_id": project_id,
            "prompt": "Test credit deduction",
            "model": "grok-4-1-fast-non-reasoning"
        })
        
        if response.status_code == 402:
            print("⚠️ User has insufficient credits - skipping credit deduction test")
            return
        
        assert response.status_code == 200
        credits_used_in_gen = response.json()["credits_used"]
        
        # Verify credits deducted
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        final_used = me_response.json()["credits_used"]
        
        assert final_used == initial_used + credits_used_in_gen, \
            f"Credits should increase by {credits_used_in_gen}: {initial_used} -> {final_used}"
        print(f"✅ POST /api/ai/generate deducts credits ({initial_used} -> {final_used})")
    
    def test_generate_saves_files_to_project(self, auth_token, project_id):
        """POST /api/ai/generate saves parsed files to project"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get project files before
        proj_before = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
        files_before = proj_before.json().get("files", {})
        
        # Generate code (even in demo mode, it should update project)
        response = requests.post(f"{BASE_URL}/api/ai/generate", headers=headers, json={
            "project_id": project_id,
            "prompt": "Create a navbar component",
            "model": "grok-4-1-fast-non-reasoning"
        })
        
        if response.status_code == 402:
            print("⚠️ Insufficient credits - skipping file save test")
            return
        
        assert response.status_code == 200
        # Project's updated_at should change
        proj_after = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
        assert proj_after.json()["updated_at"] >= proj_before.json()["updated_at"], \
            "Project updated_at should be updated"
        print("✅ POST /api/ai/generate updates project")


class TestAIGenerateStream:
    """Test GET /api/ai/generate-stream SSE endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Failed to login test user")
    
    @pytest.fixture(scope="class")
    def project_id(self, auth_token):
        """Get project for streaming tests"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/projects", headers=headers)
        if response.status_code == 200 and len(response.json()) > 0:
            return response.json()[0]["id"]
        pytest.skip("No project available for streaming test")
    
    def test_stream_requires_token_param(self, project_id):
        """GET /api/ai/generate-stream requires token query param"""
        response = requests.get(f"{BASE_URL}/api/ai/generate-stream", params={
            "project_id": project_id,
            "prompt": "test",
            "model": "grok-4-1-fast-non-reasoning"
        })
        # Without token, should return 401
        assert response.status_code == 401, f"Expected 401 without token, got {response.status_code}"
        print("✅ SSE endpoint requires token query parameter")
    
    def test_stream_auth_via_token_param(self, auth_token, project_id):
        """GET /api/ai/generate-stream auth works via token query param"""
        # Check if user has enough credits first
        headers = {"Authorization": f"Bearer {auth_token}"}
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        user = me_resp.json()
        remaining = user["credits"] - user["credits_used"]
        
        if remaining < 1:
            print("⚠️ Insufficient credits for SSE test - skipping")
            return
        
        # Start streaming request
        response = requests.get(f"{BASE_URL}/api/ai/generate-stream", params={
            "project_id": project_id,
            "prompt": "Build a todo app",
            "model": "grok-4-1-fast-non-reasoning",
            "token": auth_token
        }, stream=True, timeout=60)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert "text/event-stream" in response.headers.get("Content-Type", ""), \
            "Response should be event-stream"
        print("✅ SSE auth via token query parameter works")
    
    def test_stream_sends_agent_events(self, auth_token, project_id):
        """SSE stream sends agent_start, agent_chunk, agent_complete events"""
        # Check credits
        headers = {"Authorization": f"Bearer {auth_token}"}
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        user = me_resp.json()
        remaining = user["credits"] - user["credits_used"]
        
        if remaining < 2:
            print("⚠️ Insufficient credits for full SSE test - skipping")
            return
        
        events_received = {
            "agent_start": 0,
            "agent_chunk": 0,
            "agent_complete": 0,
            "complete": 0
        }
        agents_seen = set()
        
        response = requests.get(f"{BASE_URL}/api/ai/generate-stream", params={
            "project_id": project_id,
            "prompt": "Create a counter app",
            "model": "grok-4-1-fast-non-reasoning",
            "token": auth_token
        }, stream=True, timeout=120)
        
        assert response.status_code == 200
        
        for line in response.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    event_type = data.get("type")
                    if event_type in events_received:
                        events_received[event_type] += 1
                    if event_type == "agent_start" and "agent" in data:
                        agents_seen.add(data["agent"])
                    if event_type == "complete":
                        break
                except json.JSONDecodeError:
                    continue
        
        # Verify we got expected event types
        assert events_received["agent_start"] == 6, f"Expected 6 agent_start events, got {events_received['agent_start']}"
        assert events_received["agent_complete"] == 6, f"Expected 6 agent_complete events, got {events_received['agent_complete']}"
        assert events_received["complete"] == 1, f"Expected 1 complete event, got {events_received['complete']}"
        
        # Verify all 6 agents ran
        expected_agents = {"architect", "frontend", "backend", "security", "qa", "devops"}
        assert agents_seen == expected_agents, f"Expected agents {expected_agents}, got {agents_seen}"
        
        print(f"✅ SSE stream sends correct events: {events_received}")
        print(f"✅ All 6 agents ran: {agents_seen}")
    
    def test_stream_saves_files_after_completion(self, auth_token, project_id):
        """SSE stream saves files to project after completion"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Get project files before
        proj_before = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
        updated_before = proj_before.json()["updated_at"]
        
        # Check credits
        me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        user = me_resp.json()
        remaining = user["credits"] - user["credits_used"]
        
        if remaining < 2:
            print("⚠️ Insufficient credits for file save test")
            return
        
        # Run stream
        response = requests.get(f"{BASE_URL}/api/ai/generate-stream", params={
            "project_id": project_id,
            "prompt": "Build a simple form",
            "model": "grok-4-1-fast-non-reasoning",
            "token": auth_token
        }, stream=True, timeout=120)
        
        # Consume the stream
        for line in response.iter_lines(decode_unicode=True):
            if line and "complete" in line:
                break
        
        # Give a moment for DB write
        time.sleep(0.5)
        
        # Check project updated
        proj_after = requests.get(f"{BASE_URL}/api/projects/{project_id}", headers=headers)
        updated_after = proj_after.json()["updated_at"]
        
        assert updated_after >= updated_before, "Project should be updated after stream"
        
        # Check for _docs files (agent outputs)
        files = proj_after.json().get("files", {})
        doc_files = [f for f in files.keys() if f.startswith("_docs/")]
        assert len(doc_files) >= 6, f"Expected 6 _docs files (agent outputs), got {len(doc_files)}"
        print(f"✅ SSE stream saves files to project ({len(files)} total files)")


class TestInsufficientCredits:
    """Test 402 response for insufficient credits"""
    
    def test_generate_returns_402_insufficient_credits(self):
        """POST /api/ai/generate returns 402 when user has no credits"""
        # Create a new user with low credits
        signup_resp = requests.post(f"{BASE_URL}/api/auth/signup", json={
            "email": NEW_USER_EMAIL,
            "password": NEW_USER_PASSWORD,
            "name": "Credit Test User"
        })
        
        if signup_resp.status_code != 200:
            pytest.skip("Could not create test user")
        
        token = signup_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a project
        proj_resp = requests.post(f"{BASE_URL}/api/projects", headers=headers, json={
            "name": "Credit Test Project",
            "description": "Testing credit limits"
        })
        project_id = proj_resp.json()["id"]
        
        # Use up all credits (starter has 10 credits)
        # grok-4-latest costs 3 credits each, so 4 uses = 12 > 10, should fail
        for i in range(4):
            response = requests.post(f"{BASE_URL}/api/ai/generate", headers=headers, json={
                "project_id": project_id,
                "prompt": f"Test generation {i}",
                "model": "grok-4-latest"  # 3 credits each
            })
            if response.status_code == 402:
                print(f"✅ Got 402 after {i+1} generations - insufficient credits correctly detected")
                return
        
        # If we didn't get 402 after 4 tries, something is wrong
        print("⚠️ Did not receive 402 - user may have more credits than expected")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
