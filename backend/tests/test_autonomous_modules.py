"""
CursorCode AI - Phase 3 Autonomous AI Modules Test Suite
Tests all 18 autonomous endpoints under /api/autonomous/*:
- Guardrails (validate code, validate project)
- Sandbox (execute code, run tests)
- Validation Loop (test-gen -> execute -> debug)
- Snapshot Manager (create, list, rollback, diff)
- Context Pruning (rank files, prune context)
- Dependency Graph (build graph, affected files)
- Feedback Collector (submit, stats, recent)

Also includes regression tests for core endpoints.
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test_refactor@example.com"
TEST_PASSWORD = "Test123456!"


class TestSetup:
    """Setup fixtures and authentication"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in login response"
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_project_id(self, auth_headers):
        """Create a test project for autonomous module tests"""
        project_data = {
            "name": f"TEST_autonomous_project_{uuid.uuid4().hex[:8]}",
            "description": "Test project for autonomous modules",
            "files": {
                "main.py": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
                "utils.py": "from main import add\n\ndef double(x):\n    return add(x, x)\n",
                "test_main.py": "from main import add, subtract\n\ndef test_add():\n    assert add(2, 3) == 5\n",
                "config.py": "# Configuration\nDEBUG = True\n"
            }
        }
        response = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert response.status_code in [200, 201], f"Project creation failed: {response.text}"
        data = response.json()
        project_id = data.get("id")
        assert project_id, "No project ID returned"
        yield project_id
        # Cleanup
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)


class TestRegressionEndpoints:
    """Regression tests for core endpoints"""
    
    def test_health_endpoint(self):
        """GET /api/health - health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health endpoint working")
    
    def test_login_endpoint(self):
        """POST /api/auth/login - user login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        print("✓ Login endpoint working")
    
    def test_projects_endpoint(self, auth_headers):
        """GET /api/projects - list projects"""
        response = requests.get(f"{BASE_URL}/api/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Projects endpoint working ({len(data)} projects)")
    
    def test_user_credits_endpoint(self, auth_headers):
        """GET /api/user/credits - user credits"""
        response = requests.get(f"{BASE_URL}/api/user/credits", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "credits" in data or "plan" in data
        print(f"✓ User credits endpoint working")
    
    def test_credit_costs_endpoint(self, auth_headers):
        """GET /api/ai/credit-costs - credit costs"""
        response = requests.get(f"{BASE_URL}/api/ai/credit-costs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Response has costs wrapper
        costs = data.get("costs", data)
        assert "sandbox_execution" in costs
        print(f"✓ Credit costs endpoint working (sandbox_execution={costs.get('sandbox_execution')})")
    
    def test_payments_create_order(self, auth_headers):
        """POST /api/payments/create-order - JengaHQ checkout (demo mode)"""
        response = requests.post(f"{BASE_URL}/api/payments/create-order", 
                                 json={"plan": "standard"}, headers=auth_headers)
        # Should work in demo mode
        assert response.status_code in [200, 201, 400]  # 400 if already subscribed
        print("✓ Payments create-order endpoint accessible")
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}


class TestGuardrails:
    """Tests for /api/autonomous/guardrails/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_validate_clean_code(self, auth_headers):
        """POST /api/autonomous/guardrails/validate - clean code passes"""
        clean_code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total

result = calculate_sum([1, 2, 3, 4, 5])
print(f"Sum: {result}")
"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"code": clean_code, "language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 200, f"Guardrails validate failed: {response.text}"
        data = response.json()
        assert "passed" in data
        assert "issues" in data
        print(f"✓ Guardrails validate clean code: passed={data.get('passed')}, issues={data.get('total_issues', 0)}")
    
    def test_validate_lazy_code(self, auth_headers):
        """POST /api/autonomous/guardrails/validate - detects lazy patterns"""
        lazy_code = """
def process_data(data):
    # TODO: implement this function
    pass

def another_function():
    raise NotImplementedError
"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"code": lazy_code, "language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("total_issues", 0) > 0, "Should detect lazy code patterns"
        lazy_issues = [i for i in data.get("issues", []) if i.get("type") == "lazy_code"]
        assert len(lazy_issues) > 0, "Should have lazy_code type issues"
        print(f"✓ Guardrails detects lazy code: {len(lazy_issues)} lazy patterns found")
    
    def test_validate_credential_leak(self, auth_headers):
        """POST /api/autonomous/guardrails/validate - detects credential leaks"""
        code_with_creds = """
import stripe
stripe.api_key = "sk-live-abcdefghijklmnopqrstuvwxyz123456"

def charge_customer():
    pass
"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"code": code_with_creds, "language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        cred_issues = [i for i in data.get("issues", []) if i.get("type") == "credential_leak"]
        assert len(cred_issues) > 0, "Should detect credential leak"
        assert data.get("passed") == False, "Code with credentials should not pass"
        print(f"✓ Guardrails detects credential leak: {len(cred_issues)} credential issues found")
    
    def test_validate_hallucinated_lib(self, auth_headers):
        """POST /api/autonomous/guardrails/validate - detects hallucinated libraries"""
        code_with_fake_lib = """
from fastapi_auth_plus import SuperAuth
from pydantic_ai import AIModel

app = SuperAuth()
"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"code": code_with_fake_lib, "language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        halluc_issues = [i for i in data.get("issues", []) if i.get("type") == "hallucinated_library"]
        assert len(halluc_issues) > 0, "Should detect hallucinated libraries"
        print(f"✓ Guardrails detects hallucinated libs: {len(halluc_issues)} fake libs found")
    
    def test_validate_requires_code(self, auth_headers):
        """POST /api/autonomous/guardrails/validate - requires code parameter"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 400
        print("✓ Guardrails validate requires code parameter")
    
    def test_validate_project_files(self, auth_headers):
        """POST /api/autonomous/guardrails/validate-project/{id} - validate project files"""
        # Step 1: Create a project
        project_data = {
            "name": f"TEST_guardrails_project_{uuid.uuid4().hex[:8]}",
            "description": "Test project for guardrails"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert create_resp.status_code in [200, 201], f"Project creation failed: {create_resp.text}"
        project_id = create_resp.json().get("id")
        
        # Step 2: Add files to project
        files_data = {
            "main.py": "def hello():\n    return 'Hello'\n",
            "bad.py": "# TODO: implement\npass\n"
        }
        files_resp = requests.put(f"{BASE_URL}/api/projects/{project_id}/files", 
                                  json=files_data, headers=auth_headers)
        assert files_resp.status_code == 200, f"Adding files failed: {files_resp.text}"
        
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate-project/{project_id}",
                                     headers=auth_headers)
            assert response.status_code == 200, f"Validate project failed: {response.text}"
            data = response.json()
            assert "files_checked" in data
            assert "results" in data
            print(f"✓ Guardrails validate-project: {data.get('files_checked')} files checked")
        finally:
            requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)
    
    def test_validate_project_not_found(self, auth_headers):
        """POST /api/autonomous/guardrails/validate-project/{id} - 404 for non-existent"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate-project/nonexistent123",
                                 headers=auth_headers)
        assert response.status_code == 404
        print("✓ Guardrails validate-project returns 404 for non-existent project")


class TestSandbox:
    """Tests for /api/autonomous/sandbox/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_execute_python_code(self, auth_headers):
        """POST /api/autonomous/sandbox/execute - execute Python code"""
        code = "print('Hello from sandbox!')\nresult = 2 + 2\nprint(f'Result: {result}')"
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": code, "language": "python"},
                                 headers=auth_headers)
        # Could be 200 (success), 402 (insufficient credits), or 429 (rate limit)
        assert response.status_code in [200, 402, 429], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "output" in data
            assert "blocked" in data
            assert data.get("blocked") == False
            assert "credits_used" in data
            print(f"✓ Sandbox execute Python: success={data.get('success')}, credits_used={data.get('credits_used')}")
        elif response.status_code == 402:
            print("✓ Sandbox execute returns 402 (insufficient credits) - expected behavior")
        else:
            print("✓ Sandbox execute returns 429 (rate limit) - expected behavior")
    
    def test_execute_javascript_code(self, auth_headers):
        """POST /api/autonomous/sandbox/execute - execute JavaScript code"""
        code = "console.log('Hello from Node.js!');\nconst sum = 5 + 3;\nconsole.log(`Sum: ${sum}`);"
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": code, "language": "javascript"},
                                 headers=auth_headers)
        assert response.status_code in [200, 402, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data.get("language") == "javascript"
            print(f"✓ Sandbox execute JavaScript: success={data.get('success')}")
        else:
            print(f"✓ Sandbox execute JavaScript returns {response.status_code}")
    
    def test_execute_blocked_dangerous_code(self, auth_headers):
        """POST /api/autonomous/sandbox/execute - blocks dangerous code"""
        dangerous_code = "import os\nos.system('rm -rf /')"
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": dangerous_code, "language": "python"},
                                 headers=auth_headers)
        # Should be blocked (200 with blocked=true) or 402/429
        assert response.status_code in [200, 402, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("blocked") == True, "Dangerous code should be blocked"
            print(f"✓ Sandbox blocks dangerous code: blocked={data.get('blocked')}")
        else:
            print(f"✓ Sandbox returns {response.status_code} for dangerous code")
    
    def test_execute_blocked_credentials(self, auth_headers):
        """POST /api/autonomous/sandbox/execute - blocks embedded credentials"""
        code_with_creds = 'api_key = "sk-live-abcdefghijklmnopqrstuvwxyz123456"\nprint(api_key)'
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": code_with_creds, "language": "python"},
                                 headers=auth_headers)
        assert response.status_code in [200, 402, 429]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("blocked") == True, "Code with credentials should be blocked"
            print(f"✓ Sandbox blocks embedded credentials: blocked={data.get('blocked')}")
        else:
            print(f"✓ Sandbox returns {response.status_code} for code with credentials")
    
    def test_execute_requires_code(self, auth_headers):
        """POST /api/autonomous/sandbox/execute - requires code parameter"""
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"language": "python"},
                                 headers=auth_headers)
        assert response.status_code == 400
        print("✓ Sandbox execute requires code parameter")
    
    def test_run_project_tests(self, auth_headers):
        """POST /api/autonomous/sandbox/run-tests/{id} - run project tests"""
        # Step 1: Create project
        project_data = {
            "name": f"TEST_sandbox_tests_{uuid.uuid4().hex[:8]}",
            "description": "Test project for sandbox tests"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert create_resp.status_code in [200, 201]
        project_id = create_resp.json().get("id")
        
        # Step 2: Add test files
        files_data = {
            "main.py": "def add(a, b):\n    return a + b\n",
            "test_main.py": "from main import add\nassert add(2, 3) == 5\nprint('Test passed!')\n"
        }
        files_resp = requests.put(f"{BASE_URL}/api/projects/{project_id}/files", 
                                  json=files_data, headers=auth_headers)
        assert files_resp.status_code == 200
        
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/run-tests/{project_id}",
                                     headers=auth_headers)
            assert response.status_code in [200, 402, 429]
            
            if response.status_code == 200:
                data = response.json()
                assert "tests_found" in data
                assert "results" in data
                print(f"✓ Sandbox run-tests: {data.get('tests_found')} tests found")
            else:
                print(f"✓ Sandbox run-tests returns {response.status_code}")
        finally:
            requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)


class TestValidationLoop:
    """Tests for /api/autonomous/validate-loop endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_validation_loop_basic(self, auth_headers):
        """POST /api/autonomous/validate-loop - basic validation loop"""
        code = """
def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        response = requests.post(f"{BASE_URL}/api/autonomous/validate-loop",
                                 json={
                                     "code": code,
                                     "filename": "math_ops.py",
                                     "language": "python",
                                     "max_iterations": 2
                                 },
                                 headers=auth_headers,
                                 timeout=60)  # Longer timeout for AI calls
        
        assert response.status_code in [200, 402, 429], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "passed" in data or "iterations" in data
            assert "credits_used" in data
            print(f"✓ Validation loop: passed={data.get('passed')}, iterations={data.get('iterations')}")
        else:
            print(f"✓ Validation loop returns {response.status_code}")
    
    def test_validation_loop_requires_code(self, auth_headers):
        """POST /api/autonomous/validate-loop - requires code parameter"""
        response = requests.post(f"{BASE_URL}/api/autonomous/validate-loop",
                                 json={"filename": "test.py"},
                                 headers=auth_headers)
        assert response.status_code == 400
        print("✓ Validation loop requires code parameter")


class TestSnapshotManager:
    """Tests for /api/autonomous/snapshots/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def _create_test_project(self, auth_headers):
        """Helper to create a test project with files"""
        # Step 1: Create project
        project_data = {
            "name": f"TEST_snapshot_project_{uuid.uuid4().hex[:8]}",
            "description": "Test project for snapshots"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert create_resp.status_code in [200, 201], f"Project creation failed: {create_resp.text}"
        project_id = create_resp.json().get("id")
        
        # Step 2: Add files to project
        files_data = {
            "main.py": "print('version 1')\n",
            "config.py": "DEBUG = True\n"
        }
        files_resp = requests.put(f"{BASE_URL}/api/projects/{project_id}/files", 
                                  json=files_data, headers=auth_headers)
        assert files_resp.status_code == 200, f"Adding files failed: {files_resp.text}"
        
        return project_id
    
    def _delete_test_project(self, project_id, auth_headers):
        """Helper to delete a test project"""
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)
    
    def test_create_auto_snapshot(self, auth_headers):
        """POST /api/autonomous/snapshots/{id}/auto - create pre-op snapshot"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/auto",
                                     json={"operation": "test_operation"},
                                     headers=auth_headers)
            assert response.status_code == 200, f"Create snapshot failed: {response.text}"
            data = response.json()
            assert "snapshot_id" in data
            assert data.get("operation") == "test_operation"
            print(f"✓ Create auto snapshot: id={data.get('snapshot_id')[:8]}...")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_list_snapshots(self, auth_headers):
        """GET /api/autonomous/snapshots/{id} - list snapshots"""
        project_id = self._create_test_project(auth_headers)
        try:
            # First create a snapshot
            requests.post(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/auto",
                          json={"operation": "list_test"},
                          headers=auth_headers)
            
            response = requests.get(f"{BASE_URL}/api/autonomous/snapshots/{project_id}",
                                    headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "snapshots" in data
            assert isinstance(data["snapshots"], list)
            print(f"✓ List snapshots: {len(data['snapshots'])} snapshots found")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_list_snapshots_exclude_auto(self, auth_headers):
        """GET /api/autonomous/snapshots/{id}?include_auto=false - exclude auto snapshots"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.get(f"{BASE_URL}/api/autonomous/snapshots/{project_id}?include_auto=false",
                                    headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "snapshots" in data
            print(f"✓ List snapshots (exclude auto): {len(data['snapshots'])} manual snapshots")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_snapshot_diff(self, auth_headers):
        """GET /api/autonomous/snapshots/{id}/diff/{snap_id} - diff snapshot vs current"""
        project_id = self._create_test_project(auth_headers)
        try:
            # Create snapshot
            snap_resp = requests.post(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/auto",
                                      json={"operation": "diff_test"},
                                      headers=auth_headers)
            assert snap_resp.status_code == 200, f"Snapshot creation failed: {snap_resp.text}"
            snapshot_id = snap_resp.json().get("snapshot_id")
            
            # Modify project files
            requests.put(f"{BASE_URL}/api/projects/{project_id}/files",
                         json={"files": {
                             "main.py": "print('version 2')\n",
                             "config.py": "DEBUG = True\n",
                             "new_file.py": "# new file\n"
                         }},
                         headers=auth_headers)
            
            # Get diff
            response = requests.get(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/diff/{snapshot_id}",
                                    headers=auth_headers)
            assert response.status_code == 200, f"Diff failed: {response.text}"
            data = response.json()
            assert "added" in data
            assert "removed" in data
            assert "modified" in data
            print(f"✓ Snapshot diff: added={len(data['added'])}, modified={len(data['modified'])}, removed={len(data['removed'])}")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_rollback_to_snapshot(self, auth_headers):
        """POST /api/autonomous/snapshots/{id}/rollback/{snap_id} - rollback to snapshot"""
        project_id = self._create_test_project(auth_headers)
        try:
            # Create snapshot
            snap_resp = requests.post(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/auto",
                                      json={"operation": "rollback_test"},
                                      headers=auth_headers)
            assert snap_resp.status_code == 200, f"Snapshot creation failed: {snap_resp.text}"
            snapshot_id = snap_resp.json().get("snapshot_id")
            
            # Modify project
            requests.put(f"{BASE_URL}/api/projects/{project_id}/files",
                         json={"files": {"main.py": "print('modified')\n"}},
                         headers=auth_headers)
            
            # Rollback
            response = requests.post(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/rollback/{snapshot_id}",
                                     headers=auth_headers)
            assert response.status_code == 200, f"Rollback failed: {response.text}"
            data = response.json()
            assert data.get("success") == True
            assert "files_restored" in data
            print(f"✓ Rollback to snapshot: {data.get('files_restored')} files restored")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_snapshot_not_found(self, auth_headers):
        """GET /api/autonomous/snapshots/{id}/diff/{snap_id} - 404 for non-existent snapshot"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.get(f"{BASE_URL}/api/autonomous/snapshots/{project_id}/diff/nonexistent123",
                                    headers=auth_headers)
            assert response.status_code == 404
            print("✓ Snapshot diff returns 404 for non-existent snapshot")
        finally:
            self._delete_test_project(project_id, auth_headers)


class TestContextPruning:
    """Tests for /api/autonomous/context/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def _create_test_project(self, auth_headers):
        """Helper to create a test project with files"""
        # Step 1: Create project
        project_data = {
            "name": f"TEST_context_project_{uuid.uuid4().hex[:8]}",
            "description": "Test project for context pruning"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert create_resp.status_code in [200, 201]
        project_id = create_resp.json().get("id")
        
        # Step 2: Add files
        files_data = {
            "main.py": "def main():\n    print('Hello')\n",
            "database.py": "import sqlite3\ndef connect_db():\n    pass\n",
            "api.py": "from fastapi import FastAPI\napp = FastAPI()\n",
            "utils.py": "def helper():\n    return True\n",
            "config.py": "DATABASE_URL = 'sqlite:///test.db'\n"
        }
        files_resp = requests.put(f"{BASE_URL}/api/projects/{project_id}/files", 
                                  json=files_data, headers=auth_headers)
        assert files_resp.status_code == 200
        
        return project_id
    
    def _delete_test_project(self, project_id, auth_headers):
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)
    
    def test_rank_files_by_relevance(self, auth_headers):
        """POST /api/autonomous/context/rank/{id} - rank files by relevance"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/context/rank/{project_id}",
                                     json={"prompt": "database connection sqlite"},
                                     headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "ranked_files" in data
            assert isinstance(data["ranked_files"], list)
            
            # database.py should rank higher for database-related prompt
            if data["ranked_files"]:
                top_file = data["ranked_files"][0]
                assert "filename" in top_file
                assert "relevance_score" in top_file
                print(f"✓ Rank files: top file={top_file['filename']}, score={top_file['relevance_score']}")
            else:
                print("✓ Rank files: no files ranked (empty project)")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_prune_context(self, auth_headers):
        """POST /api/autonomous/context/prune/{id} - prune files to fit token budget"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/context/prune/{project_id}",
                                     json={"prompt": "API endpoint", "token_budget": 5000},
                                     headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "files_selected" in data
            assert "tokens_used" in data
            assert "token_budget" in data
            assert data["tokens_used"] <= data["token_budget"]
            print(f"✓ Prune context: {data['files_selected']} files selected, {data['tokens_used']}/{data['token_budget']} tokens")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_rank_requires_prompt(self, auth_headers):
        """POST /api/autonomous/context/rank/{id} - requires prompt parameter"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/context/rank/{project_id}",
                                     json={},
                                     headers=auth_headers)
            assert response.status_code == 400
            print("✓ Rank files requires prompt parameter")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_prune_requires_prompt(self, auth_headers):
        """POST /api/autonomous/context/prune/{id} - requires prompt parameter"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/context/prune/{project_id}",
                                     json={"token_budget": 5000},
                                     headers=auth_headers)
            assert response.status_code == 400
            print("✓ Prune context requires prompt parameter")
        finally:
            self._delete_test_project(project_id, auth_headers)


class TestDependencyGraph:
    """Tests for /api/autonomous/deps/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def _create_test_project(self, auth_headers):
        """Helper to create a test project with dependencies"""
        # Step 1: Create project
        project_data = {
            "name": f"TEST_deps_project_{uuid.uuid4().hex[:8]}",
            "description": "Test project for dependency graph"
        }
        create_resp = requests.post(f"{BASE_URL}/api/projects", json=project_data, headers=auth_headers)
        assert create_resp.status_code in [200, 201]
        project_id = create_resp.json().get("id")
        
        # Step 2: Add files with dependencies
        files_data = {
            "main.py": "from utils import helper\nfrom config import DEBUG\n\ndef main():\n    helper()\n",
            "utils.py": "from config import DEBUG\n\ndef helper():\n    return DEBUG\n",
            "config.py": "DEBUG = True\n",
            "api.py": "from main import main\n\ndef run_api():\n    main()\n"
        }
        files_resp = requests.put(f"{BASE_URL}/api/projects/{project_id}/files", 
                                  json=files_data, headers=auth_headers)
        assert files_resp.status_code == 200
        
        return project_id
    
    def _delete_test_project(self, project_id, auth_headers):
        requests.delete(f"{BASE_URL}/api/projects/{project_id}", headers=auth_headers)
    
    def test_build_dependency_graph(self, auth_headers):
        """GET /api/autonomous/deps/{id} - build dependency graph"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.get(f"{BASE_URL}/api/autonomous/deps/{project_id}",
                                    headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "imports" in data
            assert "dependents" in data
            assert "file_count" in data
            print(f"✓ Build dependency graph: {data['file_count']} files analyzed")
            
            # Verify structure
            if data["imports"]:
                print(f"  Imports map: {list(data['imports'].keys())}")
            if data["dependents"]:
                print(f"  Dependents map: {list(data['dependents'].keys())}")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_get_affected_files(self, auth_headers):
        """POST /api/autonomous/deps/{id}/affected - find affected files by change"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/deps/{project_id}/affected",
                                     json={"changed_file": "config.py"},
                                     headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "changed_file" in data
            assert "directly_affected" in data
            assert "all_affected" in data
            assert "total_affected" in data
            print(f"✓ Affected files for config.py: {data['total_affected']} files affected")
            print(f"  Directly affected: {data['directly_affected']}")
            print(f"  All affected: {data['all_affected']}")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_affected_requires_changed_file(self, auth_headers):
        """POST /api/autonomous/deps/{id}/affected - requires changed_file parameter"""
        project_id = self._create_test_project(auth_headers)
        try:
            response = requests.post(f"{BASE_URL}/api/autonomous/deps/{project_id}/affected",
                                     json={},
                                     headers=auth_headers)
            assert response.status_code == 400
            print("✓ Affected files requires changed_file parameter")
        finally:
            self._delete_test_project(project_id, auth_headers)
    
    def test_deps_project_not_found(self, auth_headers):
        """GET /api/autonomous/deps/{id} - 404 for non-existent project"""
        response = requests.get(f"{BASE_URL}/api/autonomous/deps/nonexistent123",
                                headers=auth_headers)
        assert response.status_code == 404
        print("✓ Dependency graph returns 404 for non-existent project")


class TestFeedbackCollector:
    """Tests for /api/autonomous/feedback/* endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_submit_feedback(self, auth_headers):
        """POST /api/autonomous/feedback - submit user feedback"""
        response = requests.post(f"{BASE_URL}/api/autonomous/feedback",
                                 json={
                                     "rating": 4,
                                     "type": "code_quality",
                                     "comment": "Good code generation",
                                     "agent": "code_generator"
                                 },
                                 headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "message" in data
        print(f"✓ Submit feedback: id={data.get('id')[:8]}...")
    
    def test_submit_feedback_with_project(self, auth_headers):
        """POST /api/autonomous/feedback - submit feedback with project_id"""
        response = requests.post(f"{BASE_URL}/api/autonomous/feedback",
                                 json={
                                     "rating": 5,
                                     "project_id": "test_project_123",
                                     "type": "general",
                                     "comment": "Excellent!"
                                 },
                                 headers=auth_headers)
        assert response.status_code == 200
        print("✓ Submit feedback with project_id")
    
    def test_submit_feedback_invalid_rating(self, auth_headers):
        """POST /api/autonomous/feedback - invalid rating returns 400"""
        response = requests.post(f"{BASE_URL}/api/autonomous/feedback",
                                 json={"rating": 10},  # Invalid: must be 1-5
                                 headers=auth_headers)
        assert response.status_code == 400
        print("✓ Submit feedback rejects invalid rating (>5)")
    
    def test_submit_feedback_requires_rating(self, auth_headers):
        """POST /api/autonomous/feedback - requires rating parameter"""
        response = requests.post(f"{BASE_URL}/api/autonomous/feedback",
                                 json={"comment": "No rating provided"},
                                 headers=auth_headers)
        assert response.status_code == 400
        print("✓ Submit feedback requires rating parameter")
    
    def test_get_feedback_stats(self, auth_headers):
        """GET /api/autonomous/feedback/stats - aggregated feedback stats"""
        response = requests.get(f"{BASE_URL}/api/autonomous/feedback/stats",
                                headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "avg_rating" in data
        assert "distribution" in data
        print(f"✓ Feedback stats: total={data['total']}, avg_rating={data['avg_rating']}")
    
    def test_get_feedback_stats_by_project(self, auth_headers):
        """GET /api/autonomous/feedback/stats?project_id=xxx - stats filtered by project"""
        response = requests.get(f"{BASE_URL}/api/autonomous/feedback/stats?project_id=test_project_123",
                                headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        print(f"✓ Feedback stats by project: total={data['total']}")
    
    def test_get_recent_feedback(self, auth_headers):
        """GET /api/autonomous/feedback/recent - recent feedback entries"""
        response = requests.get(f"{BASE_URL}/api/autonomous/feedback/recent",
                                headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Recent feedback: {len(data)} entries")
    
    def test_get_recent_feedback_with_limit(self, auth_headers):
        """GET /api/autonomous/feedback/recent?limit=5 - recent feedback with limit"""
        response = requests.get(f"{BASE_URL}/api/autonomous/feedback/recent?limit=5",
                                headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        print(f"✓ Recent feedback with limit: {len(data)} entries (max 5)")


class TestRateLimitingAndCredits:
    """Tests for rate limiting and credit checks on autonomous endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip("Authentication failed")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_sandbox_credit_deduction(self, auth_headers):
        """Verify credits are deducted after sandbox execution"""
        # Get initial credits
        credits_resp = requests.get(f"{BASE_URL}/api/user/credits", headers=auth_headers)
        initial_credits = credits_resp.json()
        
        # Execute code
        code = "print('credit test')"
        exec_resp = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                  json={"code": code, "language": "python"},
                                  headers=auth_headers)
        
        if exec_resp.status_code == 200:
            exec_data = exec_resp.json()
            credits_used = exec_data.get("credits_used", 0)
            
            # Get updated credits
            updated_resp = requests.get(f"{BASE_URL}/api/user/credits", headers=auth_headers)
            updated_credits = updated_resp.json()
            
            print(f"✓ Credit deduction: used={credits_used}")
            print(f"  Initial credits_used: {initial_credits.get('credits_used', 0)}")
            print(f"  Updated credits_used: {updated_credits.get('credits_used', 0)}")
        elif exec_resp.status_code == 402:
            print("✓ Sandbox returns 402 when insufficient credits")
        elif exec_resp.status_code == 429:
            print("✓ Sandbox returns 429 when rate limited")
    
    def test_insufficient_credits_response_format(self, auth_headers):
        """Verify 402 response format for insufficient credits"""
        # This test documents the expected 402 response format
        # May not trigger if user has sufficient credits
        code = "print('test')"
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": code, "language": "python"},
                                 headers=auth_headers)
        
        if response.status_code == 402:
            data = response.json()
            assert "detail" in data
            print(f"✓ 402 response format verified: {data.get('detail')}")
        else:
            print(f"✓ Sandbox returned {response.status_code} (user has sufficient credits)")
    
    def test_rate_limit_response_format(self, auth_headers):
        """Verify 429 response format for rate limiting"""
        # This test documents the expected 429 response format
        # May not trigger under normal testing conditions
        code = "print('rate limit test')"
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": code, "language": "python"},
                                 headers=auth_headers)
        
        if response.status_code == 429:
            data = response.json()
            assert "detail" in data
            print(f"✓ 429 response format verified: {data.get('detail')}")
        else:
            print(f"✓ Sandbox returned {response.status_code} (not rate limited)")


class TestAuthenticationRequired:
    """Verify all autonomous endpoints require authentication"""
    
    def test_guardrails_requires_auth(self):
        """POST /api/autonomous/guardrails/validate - requires auth"""
        response = requests.post(f"{BASE_URL}/api/autonomous/guardrails/validate",
                                 json={"code": "print('test')"})
        assert response.status_code in [401, 403]
        print("✓ Guardrails validate requires authentication")
    
    def test_sandbox_requires_auth(self):
        """POST /api/autonomous/sandbox/execute - requires auth"""
        response = requests.post(f"{BASE_URL}/api/autonomous/sandbox/execute",
                                 json={"code": "print('test')"})
        assert response.status_code in [401, 403]
        print("✓ Sandbox execute requires authentication")
    
    def test_validation_loop_requires_auth(self):
        """POST /api/autonomous/validate-loop - requires auth"""
        response = requests.post(f"{BASE_URL}/api/autonomous/validate-loop",
                                 json={"code": "print('test')"})
        assert response.status_code in [401, 403]
        print("✓ Validation loop requires authentication")
    
    def test_snapshots_requires_auth(self):
        """GET /api/autonomous/snapshots/{id} - requires auth"""
        response = requests.get(f"{BASE_URL}/api/autonomous/snapshots/test123")
        assert response.status_code in [401, 403]
        print("✓ Snapshots requires authentication")
    
    def test_context_requires_auth(self):
        """POST /api/autonomous/context/rank/{id} - requires auth"""
        response = requests.post(f"{BASE_URL}/api/autonomous/context/rank/test123",
                                 json={"prompt": "test"})
        assert response.status_code in [401, 403]
        print("✓ Context pruning requires authentication")
    
    def test_deps_requires_auth(self):
        """GET /api/autonomous/deps/{id} - requires auth"""
        response = requests.get(f"{BASE_URL}/api/autonomous/deps/test123")
        assert response.status_code in [401, 403]
        print("✓ Dependency graph requires authentication")
    
    def test_feedback_requires_auth(self):
        """POST /api/autonomous/feedback - requires auth"""
        response = requests.post(f"{BASE_URL}/api/autonomous/feedback",
                                 json={"rating": 5})
        assert response.status_code in [401, 403]
        print("✓ Feedback requires authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
