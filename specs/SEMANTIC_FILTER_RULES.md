DOCUMENT TITLE: API Gateway - Semantic Filtering Rules
DOCUMENT TYPE: Engineering Specification (Class G)
DOCUMENT ID: AGW-L3-RULE-001
DATE: 2026-02-27
VERSION: v1.0.0
STATUS: Active

1. AUTHORITY LINK
The Gateway MUST ingest access rules from:
`Prospera-Governance-Core/isms/DATA_ACCESS_AUTHORITY_MATRIX.md`

2. EXECUTION LOGIC (NORMATIVE)
- ON_RECEIVE: Inspect GID role and target data classification.
- INTERCEPT: If Role == AIW and Class >= C-03, emit REVOKE_SIGNAL.
