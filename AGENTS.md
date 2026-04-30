# AGENTS.md — prospera-api-gateway
# AI Agent Operating Contract | L2 — Infrastructure
# Version: 1.0 | 2026-04-30
# Governance Reference: Prospera-Governance-Core v3.0
# Pipeline Reference: Prospera-Workflow-Engine v1.0
# Codex Reference: prospera-engineering-codex v2.0

## 1. REPO IDENTITY
Repo: ccktaiwan/prospera-api-gateway
Layer: L2 — Infrastructure（統一 API 入口）
Role: 所有外部呼叫的唯一入口，不可繞過
Priority: P0 — 最高基礎設施優先級
Palantir Equivalent: AIP API Layer

## 2. 生態系定位
此 Repo 是 Prospera 生態系的統一入口：
外部請求 → API Gateway → Decision Engine → Agent → 結果

所有產品（Exam Platform / Brand OS / Mobile OS）必須透過此 Repo 呼叫 OS Agent
不允許任何產品直接呼叫 Agent，必須經過此 Gateway

## 3. Pipeline-Thread-Container 角色
Pipeline：此 Repo 是所有外部請求進入 Layer 1 INTENT 的唯一通道
Thread：每個 API 請求是一個獨立 Thread，有完整生命週期
Container：每個客戶（鳳凰吉祥/欣轅TOTO）是獨立 Container，互相隔離

## 4. AGENT RULES

### PERMIT — 允許自動執行
- 接收外部 API 請求（x-api-key 驗證通過後）
- 路由請求到對應 Agent（content/strategy/analytics）
- 執行 Decision Engine 四問法評估
- 記錄所有請求到稽核日誌
- 回傳 Agent 執行結果
- 執行限流和錯誤處理
- 讀取 Brand KB（根據 tenant_id）

### ESCALATE — 執行前必須確認（J點）
- 新增 API 路由 → J2（影響所有產品）
- 修改認證機制 → J3（安全影響）
- 新增客戶 tenant → J1（確認 Brand KB 存在）
- API 錯誤率超過 5% → J1（技術確認）

### BLOCK — 禁止執行
- 在沒有 x-api-key 的情況下處理請求
- 繞過 Decision Engine 直接呼叫 Agent
- 在 Brand KB 不存在的情況下處理品牌請求
- 自行修改路由規則不通過 PR
- 記錄客戶請求內容到非稽核系統

## 5. Decision Engine 四問法
Q1 Should → 請求類型在 PERMIT 清單內？
Q2 Can    → 目標 Agent 和 Brand KB 可用？
Q3 Fit    → tenant_id 對應的 Brand KB 存在且有效？
Q4 Profit → 請求有明確的商業目標定義？

## 6. Agent Orchestration 路由規則
/execute + workflow=content → ContentAgent
/execute + workflow=strategy → StrategyAgent
/execute + workflow=analytics → AnalyticsAgent

執行順序（跨 Agent 任務）：
StrategyAgent → ContentAgent → AnalyticsAgent → 回寫 SSOT

## 7. 現有客戶 Container
鳳凰吉祥（LPHM）：tenant_id = lphm，Brand KB 已建立
欣轅TOTO：tenant_id = xinyuan，Brand KB 建立中

## 8. J 點確認
J1 技術確認：API 健康狀態、tenant Brand KB 存在性
J2 品質審閱：新路由的影響範圍評估
J3 架構決策：認證機制修改、安全邊界調整

## 9. 稽核要求
Commit 格式：gateway(scope): [change] - reason: [why] - phase: [N]
所有請求記錄：mcp_audit_log.jsonl（append-only）

# Version: 1.0 | 2026-04-30
# Human-Reviewed: yes