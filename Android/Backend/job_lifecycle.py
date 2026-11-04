"""Shared state machine for canonical job statuses."""

JOB_TRANSITIONS = {
    "open": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"completed"},
    "completed": set(),
    "cancelled": set(),
}

# Work starts and completion are performed through dedicated, role-checked
# endpoints. This table is also used by the Admin Portal's status guard.

VALID_JOB_STATUSES = frozenset(JOB_TRANSITIONS)


def can_transition(current: str, target: str) -> bool:
    return target in JOB_TRANSITIONS.get(current, set())
