import requests
import sys
import json
import uuid
from datetime import datetime

class CursorCodeAPITester:
    def __init__(self, base_url="https://grok-devops.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.project_id = None
        self.deployment_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.test_user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        self.test_user_name = "Test User"
        self.test_user_password = "TestPass123!"

    def log_test(self, name, success, details="", expected_status=None, actual_status=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
            if expected_status and actual_status:
                print(f"   Expected status: {expected_status}, Got: {actual_status}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "expected_status": expected_status,
            "actual_status": actual_status
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if headers:
            test_headers.update(headers)
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            
            if success:
                self.log_test(name, True)
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                error_detail = ""
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', str(error_data))
                except:
                    error_detail = response.text[:200]
                
                self.log_test(name, False, error_detail, expected_status, response.status_code)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Request failed: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test backend health check"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_signup(self):
        """Test user signup - should create unverified user"""
        success, response = self.run_test(
            "User Signup",
            "POST",
            "auth/signup",
            200,
            data={
                "email": self.test_user_email,
                "name": self.test_user_name,
                "password": self.test_user_password
            }
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user']['id']
                # Check if user is unverified
                if not response['user'].get('email_verified', True):
                    print(f"   ✅ User created as unverified (email_verified=false)")
                else:
                    print(f"   ⚠️  User created as verified (expected unverified)")
            return True
        return False

    def test_login(self):
        """Test user login without GitHub"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data={
                "email": self.test_user_email,
                "password": self.test_user_password
            }
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            return True
        return False

    def test_get_me(self):
        """Test get current user info"""
        return self.run_test("Get Current User", "GET", "auth/me", 200)

    def test_resend_verification(self):
        """Test resend verification email"""
        return self.run_test("Resend Verification Email", "POST", "auth/resend-verification", 200)

    def test_github_oauth_initiation(self):
        """Test GitHub OAuth initiation - should return auth URL"""
        success, response = self.run_test("GitHub OAuth Initiation", "GET", "auth/github", 200)
        
        if success and 'url' in response:
            print(f"   ✅ GitHub auth URL returned: {response['url'][:50]}...")
            return True
        elif success:
            print(f"   ❌ No 'url' field in response: {response}")
        return False

    def test_github_repos_without_token(self):
        """Test GitHub repos endpoint without GitHub token - should fail"""
        success, response = self.run_test("GitHub Repos (No Token)", "GET", "github/repos", 400)
        return success

    def test_plans_endpoint(self):
        """Test subscription plans endpoint"""
        success, response = self.run_test("Get Subscription Plans", "GET", "plans", 200)
        
        if success and 'plans' in response:
            plans = response['plans']
            print(f"   ✅ Found {len(plans)} subscription plans")
            for plan_name, plan_data in plans.items():
                print(f"      - {plan_name}: ${plan_data.get('price', 0)}/month, {plan_data.get('credits', 0)} credits")
            return True
        return False

    def test_stripe_checkout_demo_mode(self):
        """Test Stripe checkout creation in demo mode"""
        success, response = self.run_test(
            "Stripe Checkout (Demo Mode)",
            "POST",
            "subscriptions/create-checkout?plan=standard",
            200
        )
        
        if success and 'url' in response:
            if response.get('demo'):
                print(f"   ✅ Demo mode checkout URL: {response['url']}")
            else:
                print(f"   ✅ Checkout URL: {response['url']}")
            return True
        return False

    def test_create_project(self):
        """Test project creation"""
        success, response = self.run_test(
            "Create Project",
            "POST",
            "projects",
            200,
            data={
                "name": "Test Project",
                "description": "A test project for API testing"
            }
        )
        
        if success and 'id' in response:
            self.project_id = response['id']
            print(f"   ✅ Project created with ID: {self.project_id}")
            return True
        return False

    def test_get_projects(self):
        """Test get user projects"""
        return self.run_test("Get Projects", "GET", "projects", 200)

    def test_deploy_project(self):
        """Test project deployment"""
        if not hasattr(self, 'project_id') or not self.project_id:
            print("   ⚠️  Skipping deploy test - no project created")
            return False
            
        success, response = self.run_test(
            "Deploy Project",
            "POST",
            f"deploy/{self.project_id}",
            200
        )
        
        if success and 'deployed_url' in response:
            print(f"   ✅ Project deployed to: {response['deployed_url']}")
            self.deployment_id = response.get('deployment_id')
            return True
        return False

    def test_list_deployments(self):
        """Test list deployments"""
        success, response = self.run_test("List Deployments", "GET", "deployments", 200)
        
        if success and 'deployments' in response:
            deployments = response['deployments']
            print(f"   ✅ Found {len(deployments)} deployments")
            return True
        return False

    def test_ai_models(self):
        """Test AI models endpoint"""
        success, response = self.run_test("Get AI Models", "GET", "ai/models", 200)
        
        if success and 'models' in response:
            models = response['models']
            print(f"   ✅ Found {len(models)} AI models")
            for model in models:
                print(f"      - {model.get('name', 'Unknown')}: {model.get('credits_per_use', 0)} credits")
            return True
        return False

    def test_current_subscription(self):
        """Test current subscription endpoint"""
        return self.run_test("Get Current Subscription", "GET", "subscriptions/current", 200)

    def run_all_tests(self):
        """Run all backend API tests"""
        print("🚀 Starting CursorCode AI Backend API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Test User: {self.test_user_email}")
        print("=" * 60)

        # Basic health checks
        self.test_health_check()
        self.test_root_endpoint()
        
        # Authentication flow
        self.test_signup()
        self.test_get_me()
        self.test_resend_verification()
        self.test_login()  # Test login after signup
        
        # GitHub OAuth (without actual GitHub credentials)
        self.test_github_oauth_initiation()
        self.test_github_repos_without_token()
        
        # Subscription and billing
        self.test_plans_endpoint()
        self.test_stripe_checkout_demo_mode()
        self.test_current_subscription()
        
        # Projects and deployment
        self.test_create_project()
        self.test_get_projects()
        self.test_deploy_project()
        self.test_list_deployments()
        
        # AI features
        self.test_ai_models()

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
            print("\nFailed tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['name']}: {result['details']}")
            return 1

def main():
    tester = CursorCodeAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())