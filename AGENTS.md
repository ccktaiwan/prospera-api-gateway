# AGENTS.md — prospera-api-gateway
# AI Agent Operating Contract | Infrastructure — 統一入口
# Version: 1.0 | 2026-04-26

## 1. REPO IDENTITY

Repo: ccktaiwan/prospera-api-gateway
Layer: 基礎設施層（橫跨所有層）
Role: 生態系唯一 API 入口，所有產品的統一調用點
成熟度: 開發中，最高優先
核心原則: 沒有 Gateway，所有產品都是孤島
Governance Reference: Prospera-Governance-Core v1.0
Codex Reference: prospera-engineering-codex v1.0

## 2. 不污染原則（強制）

應用層（L5）-> API Gateway -> 引擎層（L3/L4）-> OS（L1）

任何跳過 Gateway 直接存取底層的行為 = 架構違規 = BLOCK

## 3. 核心職責

| 職責 | 說明 |
|------|------|
| 統一入口 | 所有外部呼叫只能透過 Gateway |
| 流量治理 | Rate limiting / 請求驗證 / 路由分發 |
| 身份驗證橋接 | 與 prospera-identity-authority 聯動，驗證 GID 身份鏈 |
| 稽核日誌 | 所有請求寫入 prospera-audit-ledger |
| 服務發現 | 依照 prospera-registry 找到正確的 Engine 或 Agent |

## 4. MVP 功能定義

| 功能 | 要求 |
|------|------|
| 路由分發 | 能路由到 content / strategy / analytics Agent |
| API Key 驗證 | x-api-key header 驗證（與 MCP Server 對齊） |
| 稽核日誌 | 所有請求自動寫入 mcp_audit_log.jsonl |
| 錯誤處理 | 標準化格式（4xx / 5xx），含 Governance 錯誤碼 |
| 健康檢查 | GET /health — 確認 Gateway 和下游 Agent 狀態 |

## 5. AGENT RULES

### PERMIT — 允許執行
- 新增路由規則（對應新的 Agent 或 Engine）
- 修改 Rate Limiting 參數
- 新增請求驗證邏輯

### ESCALATE — 執行前必須確認
- 修改 API Key 驗證機制（涉及 Identity Authority）
- 修改稽核日誌結構（涉及 audit-ledger 的讀取格式）

### BLOCK — 禁止執行
- 允許任何應用層繞過 Gateway 呼叫底層
- 在沒有 GID 身份鏈驗證的情況下放行請求
- 自行修改 prospera-registry 的服務發現邏輯

## 6. J 點確認

J1 架構確認：新增路由或修改驗證機制前暫停，等待人確認
J2 PR Review：MVP 功能完成後建立 PR，暫停
J3 部署確認：CI/CD 通過後確認下游整合測試完成，暫停

## 7. 整合順序

Step 1: 包裝 prospera-os MCP Server 路由，讓外部統一呼叫
Step 2: 整合 prospera-identity-authority，GID 身份鏈驗證
Step 3: 接上 prospera-exam-platform，第一個受治理的應用
Step 4: 整合 prospera-audit-ledger，所有請求全程可追溯

Gateway 完成後，Prospera OS 才從「存在」升級到「可被使用」。

# AI-GENERATED DOCUMENT
# Generated: 2026-04-26T00:00:00Z
# Model: claude-sonnet-4-6
# Phase: infra
# Repo: prospera-api-gateway
# Governance: prospera-engineering-codex v1.0
# Human-Reviewed: no