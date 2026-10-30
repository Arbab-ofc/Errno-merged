"""Shared state machine for canonical job statuses."""

JOB_TRANSITIONS = {
    "open": {"assigned", "cancelled"},
    "assigned": {"in_progress", "inProgress", "completed", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "inProgress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}

VALID_JOB_STATUSES = frozenset(JOB_TRANSITIONS)


def can_transition(current: str, target: str) -> bool:
    return target in JOB_TRANSITIONS.get(current, set())
