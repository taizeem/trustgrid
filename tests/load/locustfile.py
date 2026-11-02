import uuid
import jwt
import datetime
from locust import HttpUser, task, between

class TrustGridTenantUser(HttpUser):
    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Generate valid tenant JWT token for load testing
        self.tenant_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())
        secret = "dev_insecure_jwt_secret_key_minimum_32_bytes_long_123"
        payload = {
            "sub": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": ["admin"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }
        self.token = jwt.encode(payload, secret, algorithm="HS256")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(4)
    def query_vendors(self):
        self.client.get("/api/v1/vendors/", headers=self.headers, name="/api/v1/vendors/ [List]")

    @task(2)
    def create_vendor_and_risk_evaluation(self):
        # 1. Create vendor profile
        vendor_payload = {
            "name": f"Vendor-{uuid.uuid4().hex[:6]}",
            "website": "https://example.com"
        }
        with self.client.post("/api/v1/vendors/", json=vendor_payload, headers=self.headers, catch_response=True) as resp:
            if resp.status_code == 201:
                vendor_id = resp.json().get("id")
                # 2. Compute risk score synchronously via Rust service
                risk_payload = {
                    "vendor_id": vendor_id,
                    "answers": {"q1": "compliant", "q2": "non_compliant"}
                }
                self.client.post("/api/v1/risk/compute", json=risk_payload, headers=self.headers, name="/api/v1/risk/compute")
            else:
                resp.failure(f"Failed to create vendor: {resp.text}")

    @task(1)
    def check_billing_entitlements(self):
        self.client.get(
            "/api/v1/billing/entitlements/check/?feature=max_vendors&quantity=1",
            headers=self.headers,
            name="/api/v1/billing/entitlements/check/"
        )