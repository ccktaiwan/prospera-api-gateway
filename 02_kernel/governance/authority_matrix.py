"""
Authority Matrix + State Machine
Phase: L4 Governance
Governing Codex: prospera-engineering-codex v1.0
Human-Reviewed: PENDING
"""

AUTHORITY_MATRIX = {
    "admin":    {"read": True,  "write": True,  "delete": True,  "deploy": True},
    "operator": {"read": True,  "write": True,  "delete": False, "deploy": False},
    "auditor":  {"read": True,  "write": False, "delete": False, "deploy": False},
    "external": {"read": False, "write": False, "delete": False, "deploy": False},
}

STATE_MACHINE = {
    "INIT":    ["ACTIVE", "FAILED"],
    "ACTIVE":  ["SUSPENDED", "COMPLETED", "FAILED"],
    "SUSPENDED": ["ACTIVE", "TERMINATED"],
    "COMPLETED": ["ARCHIVED"],
    "FAILED":  ["INIT", "TERMINATED"],
    "TERMINATED": [],
    "ARCHIVED": [],
}

def check_permission(role: str, action: str) -> bool:
    return AUTHORITY_MATRIX.get(role, {}).get(action, False)

def get_next_states(current: str) -> list:
    return STATE_MACHINE.get(current, [])

def validate_transition(from_state: str, to_state: str) -> bool:
    return to_state in STATE_MACHINE.get(from_state, [])
