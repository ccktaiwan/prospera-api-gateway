"""
Prospera API Gateway - v1.1
GID Identity Chain + Persistent Startup
Phase: Infrastructure v1.1
"""
import os
import json
import datetime
import hashlib
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import uvicorn

# ── Config ──────────────────────────────────────────────────────
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "prospera-gateway-dev-key")
OS_MCP_URL      = os.environ.get("OS_MCP_URL", "http://127.0.0.1:8000")
OS_MCP_KEY      = os.environ.get("OS_MCP_KEY", "prospera-local-dev-key")
AUDIT_LOG       = Path(os.environ.get("GATEWAY_AUDIT_LOG", "gateway_audit.jsonl"))

# ── GID Tenant Registry（本地輕量版，之後接 identity-authority）──
GID_REGISTRY = {
    "exam-001":     {"name": "Exam Platform",    "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "exam-demo-001":{"name": "Exam Demo",        "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "test-001":     {"name": "Test Tenant",      "status": "ACTIVE", "allowed": ["content","strategy","analytics"]},
    "phoenix-001":  {"name": "Phoenix Jixiang",  "status": "ACTIVE", "allowed": ["content","strategy"]},
}

def resolve_gid(tenant_id: str) -> dict:
    if tenant_id in GID_REGISTRY:
        return GID_REGISTRY[tenant_id]
    return {"name": tenant_id, "status": "UNKNOWN", "allowed": []}

def generate_gid_token(tenant_id: str, workflow: str, timestamp: str) -> str:
    raw = f"{tenant_id}:{workflow}:{timestamp}:prospera-governance"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]

# ── App ─────────────────────────────────────────────────────────
app = FastAPI(
    title="Prospera API Gateway",
    description="Unified entry point for Prospera OS ecosystem",
    version="1.1.0"
)

# ── Audit ────────────────────────────────────────────────────────
def write_audit(tenant_id: str, workflow: str, status: str, gid_token: str = "", detail: str = ""):
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

# ── Models ───────────────────────────────────────────────────────
class GatewayRequest(BaseModel):
    tenant_id: str
    workflow: str
    prompt: str
    context: dict = {}

# ── Routes ───────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "OK",
        "gateway": "Prospera API Gateway v1.1",
        "upstream": OS_MCP_URL,
        "gid": "local-registry",
        "tenants": len(GID_REGISTRY)
    }

@app.get("/v1/identity/{tenant_id}")
def identity(tenant_id: str, x_api_key: str = Header(...)):
    if x_api_key != GATEWAY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    gid = resolve_gid(tenant_id)
    return {"tenant_id": tenant_id, "gid": gid}

@app.post("/v1/execute")
async def execute(request: GatewayRequest, x_api_key: str = Header(...)):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    gid_token = generate_gid_token(request.tenant_id, request.workflow, ts)

    # API Key 驗證
    if x_api_key != GATEWAY_API_KEY:
        write_audit(request.tenant_id, request.workflow, "REJECTED", gid_token, "Invalid API key")
        raise HTTPException(status_code=401, detail="Invalid API key")

    # GID 身份鏈驗證
    gid = resolve_gid(request.tenant_id)
    if gid["status"] == "UNKNOWN":
        write_audit(request.tenant_id, request.workflow, "BLOCKED", gid_token, "Unknown tenant GID")
        raise HTTPException(status_code=403, detail=f"Unknown tenant: {request.tenant_id}. Register GID first.")
    if gid["status"] != "ACTIVE":
        write_audit(request.tenant_id, request.workflow, "BLOCKED", gid_token, f"Tenant status: {gid['status']}")
        raise HTTPException(status_code=403, detail=f"Tenant {request.tenant_id} is {gid['status']}")
    if request.workflow not in gid["allowed"]:
        write_audit(request.tenant_id, request.workflow, "BLOCKED", gid_token, "Workflow not permitted for tenant")
        raise HTTPException(status_code=403, detail=f"Workflow '{request.workflow}' not permitted for {request.tenant_id}")

    # Workflow 驗證
    if request.workflow not in ["content", "strategy", "analytics"]:
        write_audit(request.tenant_id, request.workflow, "REJECTED", gid_token, "Unknown workflow")
        raise HTTPException(status_code=400, detail=f"Unknown workflow: {request.workflow}")

    # 轉發到 OS MCP Server
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OS_MCP_URL}/execute",
                json={
                    "tenant_id": request.tenant_id,
                    "workflow": request.workflow,
                    "prompt": request.prompt,
                    "context": request.context
                },
                headers={"x-api-key": OS_MCP_KEY}
            )
            result = response.json()
            write_audit(request.tenant_id, request.workflow, "SUCCESS", gid_token)
            return {
                "status": "SUCCESS",
                "gateway": "v1.1",
                "tenant_id": request.tenant_id,
                "gid_token": gid_token,
                "workflow": request.workflow,
                "result": result
            }
    except httpx.ConnectError:
        write_audit(request.tenant_id, request.workflow, "ERROR", gid_token, "OS MCP Server unreachable")
        raise HTTPException(status_code=503, detail="OS MCP Server unreachable. Start prospera-os first.")
    except Exception as e:
        write_audit(request.tenant_id, request.workflow, "ERROR", gid_token, str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("[Gateway] Starting Prospera API Gateway v1.1 on http://localhost:9000")
    print(f"[Gateway] Upstream OS MCP: {OS_MCP_URL}")
    print(f"[Gateway] GID Registry: {len(GID_REGISTRY)} tenants")
    uvicorn.run(app, host="127.0.0.1", port=9000)