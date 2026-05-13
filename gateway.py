"""
Prospera API Gateway - v1.2
GID Identity Chain + Auth Service + Usage Ledger Integration
"""
import os, json, datetime, hashlib, httpx, sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

IDENTITY_AUTHORITY_PATH = Path(r"C:\AI_WorkDir\GitHub\prospera-identity-authority")
AUDIT_LEDGER_PATH = Path(r"C:\AI_WorkDir\GitHub\prospera-audit-ledger")

if str(IDENTITY_AUTHORITY_PATH) not in sys.path:
    sys.path.insert(0, str(IDENTITY_AUTHORITY_PATH))
if str(AUDIT_LEDGER_PATH) not in sys.path:
    sys.path.insert(0, str(AUDIT_LEDGER_PATH))

try:
    from auth_service import AuthService
    auth_service = AuthService()
    AUTH_SERVICE_AVAILABLE = True
    print("[Gateway] auth_service loaded ✅")
except ImportError:
    AUTH_SERVICE_AVAILABLE = False
    print("[Gateway] auth_service fallback to API key mode")

try:
    from usage_ledger import log_usage
    USAGE_LEDGER_AVAILABLE = True
    print("[Gateway] usage_ledger loaded ✅")
except ImportError:
    USAGE_LEDGER_AVAILABLE = False
    print("[Gateway] usage_ledger unavailable")

GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "prospera-gateway-dev-key")
OS_MCP_URL      = os.environ.get("OS_MCP_URL", "http://127.0.0.1:8000")
OS_MCP_KEY      = os.environ.get("OS_MCP_KEY", "prospera-local-dev-key")
AUDIT_LOG       = Path(os.environ.get("GATEWAY_AUDIT_LOG", "gateway_audit.jsonl"))

GID_REGISTRY = {
    "exam-001":      {"name": "Exam Platform",   "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "exam-demo-001": {"name": "Exam Demo",        "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "test-001":      {"name": "Test Tenant",      "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "phoenix-001":   {"name": "Phoenix Jixiang",  "status": "ACTIVE", "allowed": ["content","strategy"]},
    "TENANT_PHOENIX":{"name": "Phoenix Jixiang",  "status": "ACTIVE", "allowed": ["content","strategy"]},
    "TENANT_ESG":    {"name": "ESG Platform",     "status": "ACTIVE", "allowed": ["content","analytics"]},
}

def resolve_gid(tenant_id):
    return GID_REGISTRY.get(tenant_id, {"name": tenant_id, "status": "UNKNOWN", "allowed": []})

def generate_gid_token(tenant_id, workflow, timestamp):
    raw = f"{tenant_id}:{workflow}:{timestamp}:prospera-governance"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

app = FastAPI(title="Prospera API Gateway", version="1.2.0")

def write_audit(tenant_id, workflow, status, gid_token="", detail=""):
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "api-gateway",
        "tenant_id": tenant_id,
        "workflow": workflow,
        "gid_token": gid_token,
        "status": status,
        "detail": detail
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

class GatewayRequest(BaseModel):
    tenant_id: str
    workflow: str
    prompt: str
    context: dict = {}
    token: str = ""

@app.get("/health")
def health():
    return {
        "status": "OK",
        "gateway": "Prospera API Gateway v1.2",
        "upstream": OS_MCP_URL,
        "auth_service": "connected" if AUTH_SERVICE_AVAILABLE else "fallback",
        "usage_ledger": "connected" if USAGE_LEDGER_AVAILABLE else "unavailable",
        "tenants": len(GID_REGISTRY)
    }

@app.get("/v1/identity/{tenant_id}")
def identity(tenant_id: str, x_api_key: str = Header(...)):
    if x_api_key != GATEWAY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return {"tenant_id": tenant_id, "gid": resolve_gid(tenant_id)}

@app.post("/v1/execute")
async def execute(request: GatewayRequest, x_api_key: str = Header(...)):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    resolved_tenant_id = request.tenant_id

    if request.token and AUTH_SERVICE_AVAILABLE:
        try:
            resolved_tenant_id = auth_service.authenticate(request.token)
        except RuntimeError as e:
            write_audit(request.tenant_id, request.workflow, "REJECTED", "", str(e))
            raise HTTPException(status_code=401, detail=str(e))
    else:
        if x_api_key != GATEWAY_API_KEY:
            write_audit(request.tenant_id, request.workflow, "REJECTED", "", "Invalid API key")
            raise HTTPException(status_code=401, detail="Invalid API key")

    gid_token = generate_gid_token(resolved_tenant_id, request.workflow, ts)
    gid = resolve_gid(resolved_tenant_id)

    if gid["status"] == "UNKNOWN":
        write_audit(resolved_tenant_id, request.workflow, "BLOCKED", gid_token, "Unknown tenant")
        raise HTTPException(status_code=403, detail=f"Unknown tenant: {resolved_tenant_id}")
    if gid["status"] != "ACTIVE":
        write_audit(resolved_tenant_id, request.workflow, "BLOCKED", gid_token, "Tenant inactive")
        raise HTTPException(status_code=403, detail=f"Tenant {resolved_tenant_id} is {gid['status']}")
    if request.workflow not in gid["allowed"]:
        write_audit(resolved_tenant_id, request.workflow, "BLOCKED", gid_token, "Workflow not permitted")
        raise HTTPException(status_code=403, detail=f"Workflow not permitted")
    if request.workflow not in ["content", "strategy", "analytics"]:
        write_audit(resolved_tenant_id, request.workflow, "REJECTED", gid_token, "Unknown workflow")
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {request.workflow}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OS_MCP_URL}/execute",
                json={"tenant_id": resolved_tenant_id, "workflow": request.workflow,
                      "prompt": request.prompt, "context": request.context},
                headers={"x-api-key": OS_MCP_KEY}
            )
            result = response.json()
            if USAGE_LEDGER_AVAILABLE:
                log_usage(tenant_id=resolved_tenant_id, units=1)
            write_audit(resolved_tenant_id, request.workflow, "SUCCESS", gid_token)
            return {
                "status": "SUCCESS", "gateway": "v1.2",
                "tenant_id": resolved_tenant_id, "gid_token": gid_token,
                "workflow": request.workflow, "usage_logged": USAGE_LEDGER_AVAILABLE,
                "result": result
            }
    except httpx.ConnectError:
        write_audit(resolved_tenant_id, request.workflow, "ERROR", gid_token, "OS MCP unreachable")
        raise HTTPException(status_code=503, detail="OS MCP Server unreachable. Start prospera-os first.")
    except Exception as e:
        write_audit(resolved_tenant_id, request.workflow, "ERROR", gid_token, str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print(f"[Gateway] Starting v1.2 | Auth: {'✅' if AUTH_SERVICE_AVAILABLE else '⚠️ fallback'} | Ledger: {'✅' if USAGE_LEDGER_AVAILABLE else '⚠️'}")
    uvicorn.run(app, host="127.0.0.1", port=9000)
