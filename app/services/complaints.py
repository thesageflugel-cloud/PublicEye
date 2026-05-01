from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ALLOWED_IMAGE_TYPES, UPLOAD_DIR
from app.models import Complaint, ComplaintStatus, ComplaintUpdate, PriorityLevel, RoleEnum, User


PRIORITY_SLA_HOURS = {
    PriorityLevel.LOW: 72,
    PriorityLevel.MEDIUM: 48,
    PriorityLevel.HIGH: 24,
    PriorityLevel.CRITICAL: 12,
}

STATUS_TRANSITIONS = {
    ComplaintStatus.NEW: {ComplaintStatus.ASSIGNED},
    ComplaintStatus.ASSIGNED: {ComplaintStatus.IN_PROGRESS, ComplaintStatus.RESOLVED},
    ComplaintStatus.IN_PROGRESS: {ComplaintStatus.RESOLVED},
    ComplaintStatus.RESOLVED: {ComplaintStatus.CLOSED, ComplaintStatus.IN_PROGRESS},
    ComplaintStatus.CLOSED: set(),
}


def generate_reference_code() -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    short_id = uuid.uuid4().hex[:6].upper()
    return f"PE-{timestamp}-{short_id}"


def calculate_due_at(priority: PriorityLevel) -> datetime:
    return datetime.utcnow() + timedelta(hours=PRIORITY_SLA_HOURS[priority])


def can_transition(current_status: ComplaintStatus, target_status: ComplaintStatus) -> bool:
    return target_status in STATUS_TRANSITIONS[current_status]


def save_upload(file: UploadFile | None, subfolder: str = "") -> str | None:
    if file is None or not getattr(file, "filename", None):
        return None
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Unsupported file type. Please upload PNG, JPG, or WEBP images only.")
    target_folder = UPLOAD_DIR / subfolder if subfolder else UPLOAD_DIR
    target_folder.mkdir(parents=True, exist_ok=True)
    extension = Path(file.filename).suffix.lower() or ".jpg"
    file_name = f"{uuid.uuid4().hex}{extension}"
    destination = target_folder / file_name
    with destination.open("wb") as upload_stream:
        upload_stream.write(file.file.read())
    relative_path = destination.relative_to(UPLOAD_DIR.parent).as_posix()
    return f"/{relative_path}"


def add_update(
    db: Session,
    complaint: Complaint,
    actor: User,
    update_type: str,
    message: str,
    previous_status: str | None = None,
    new_status: str | None = None,
    attachment_path: str | None = None,
) -> ComplaintUpdate:
    update = ComplaintUpdate(
        complaint=complaint,
        actor=actor,
        update_type=update_type,
        message=message,
        previous_status=previous_status,
        new_status=new_status,
        attachment_path=attachment_path,
    )
    db.add(update)
    return update


def refresh_escalations(db: Session) -> None:
    now = datetime.utcnow()
    open_statuses = (
        ComplaintStatus.NEW,
        ComplaintStatus.ASSIGNED,
        ComplaintStatus.IN_PROGRESS,
    )
    complaints = db.execute(
        select(Complaint).where(Complaint.status.in_(open_statuses), Complaint.due_at.is_not(None))
    ).scalars().all()
    changed = False
    system_user = db.execute(select(User).where(User.role == RoleEnum.ADMIN).order_by(User.id)).scalars().first()
    for complaint in complaints:
        if complaint.due_at is None or now <= complaint.due_at:
            continue
        overdue_hours = (now - complaint.due_at).total_seconds() / 3600
        computed_level = 1
        if overdue_hours >= 24:
            computed_level = 2
        if overdue_hours >= 48:
            computed_level = 3
        if computed_level > complaint.escalation_level:
            complaint.escalation_level = computed_level
            changed = True
            if system_user:
                add_update(
                    db,
                    complaint,
                    system_user,
                    update_type="escalation",
                    message=f"SLA breach detected. Escalation level raised to {computed_level}.",
                )
    if changed:
        db.commit()


def complaint_visible_to(user: User, complaint: Complaint) -> bool:
    if user.role == RoleEnum.ADMIN:
        return True
    if user.role == RoleEnum.CITIZEN:
        return complaint.citizen_id == user.id
    officer_department_id = user.department_id
    return complaint.assigned_officer_id == user.id or (
        officer_department_id is not None and complaint.department_id == officer_department_id
    )


def serialize_coordinates(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.6f}"
