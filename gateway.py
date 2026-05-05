"""
Prospera API Gateway - MVP v1.0
Routes external requests to prospera-os MCP Server
Phase: Infrastructure MVP
"""
import os
import json
import datetime
import httpx
from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# ── Config ──────────────────────────────────────────────────────
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "prospera-gateway-dev-key")
OS_MCP_URL      = os.environ.get("OS_MCP_URL", "http://127.0.0.1:8000")
OS_MCP_KEY      = os.environ.get("OS_MCP_KEY", "prospera-local-dev-key")
AUDIT_LOG       = Path(os.environ.get("GATEWAY_AUDIT_LOG", "gateway_audit.jsonl"))

# ── App ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Prospera API Gateway",
    description="Unified entry point for Prospera OS ecosystem",
    version="1.0.0"
)

# ── Audit ────────────────────────────────────────────────────────
def write_audit(tenant_id: str, workflow: str, status: str, detail: str = ""):
    entry = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "api-gateway",
        "tenant_id": tenant_id,
        "workflow": workflow,
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
        "gateway": "Prospera API Gateway v1.0",
        "upstream": OS_MCP_URL
    }

@app.post("/v1/execute")
async def execute(request: GatewayRequest, x_api_key: str = Header(...)):

    # API Key 驗證
    if x_api_key != GATEWAY_API_KEY:
        write_audit(request.tenant_id, request.workflow, "REJECTED", "Invalid API key")
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Workflow 驗證
    if request.workflow not in ["content", "strategy", "analytics"]:
        write_audit(request.tenant_id, request.workflow, "REJECTED", "Unknown workflow")
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
            write_audit(request.tenant_id, request.workflow, "SUCCESS")
            return {
                "status": "SUCCESS",
                "gateway": "v1.0",
                "tenant_id": request.tenant_id,
                "workflow": request.workflow,
                "result": result
            }
    except httpx.ConnectError:
        write_audit(request.tenant_id, request.workflow, "ERROR", "OS MCP Server unreachable")
        raise HTTPException(status_code=503, detail="OS MCP Server unreachable. Start prospera-os first.")
    except Exception as e:
        write_audit(request.tenant_id, request.workflow, "ERROR", str(e))
        raise HTTPException(status_code=500, detail=str(e))

# ── Entry ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[Gateway] Starting Prospera API Gateway on http://localhost:9000")
    print(f"[Gateway] Upstream OS MCP: {OS_MCP_URL}")
    uvicorn.run(app, host="127.0.0.1", port=9000)