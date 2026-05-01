from app.models import ComplaintStatus
from app.services.complaints import can_transition


def test_valid_status_transition():
    assert can_transition(ComplaintStatus.NEW, ComplaintStatus.ASSIGNED)
    assert can_transition(ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED)


def test_invalid_status_transition():
    assert not can_transition(ComplaintStatus.NEW, ComplaintStatus.RESOLVED)
    assert not can_transition(ComplaintStatus.CLOSED, ComplaintStatus.NEW)
