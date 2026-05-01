from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Complaint, ComplaintStatus, Department, User


def get_all_complaints(db: Session) -> list[Complaint]:
    return db.execute(
        select(Complaint)
        .options(
            joinedload(Complaint.citizen),
            joinedload(Complaint.department),
            joinedload(Complaint.assigned_officer),
        )
        .order_by(Complaint.created_at.desc())
    ).unique().scalars().all()


def overall_metrics(db: Session) -> dict:
    complaints = get_all_complaints(db)
    status_counts = Counter(complaint.status.value for complaint in complaints)
    department_counts = defaultdict(lambda: {"total": 0, "resolved": 0, "avg_hours": 0.0})
    resolved_durations = []
    escalated_count = 0

    for complaint in complaints:
        department_name = complaint.department.name if complaint.department else "Unassigned"
        department_counts[department_name]["total"] += 1
        if complaint.status in {ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED}:
            department_counts[department_name]["resolved"] += 1
            if complaint.resolved_at:
                hours = (complaint.resolved_at - complaint.created_at).total_seconds() / 3600
                resolved_durations.append(hours)
                department_counts[department_name]["avg_hours"] += hours
        if complaint.escalation_level > 0:
            escalated_count += 1

    department_summary = []
    for department_name, values in department_counts.items():
        total = values["total"]
        resolved = values["resolved"]
        avg_hours = round(values["avg_hours"] / resolved, 1) if resolved else 0.0
        department_summary.append(
            {
                "name": department_name,
                "total": total,
                "resolved": resolved,
                "open": total - resolved,
                "avg_hours": avg_hours,
            }
        )
    department_summary.sort(key=lambda row: row["total"], reverse=True)

    average_resolution_hours = round(sum(resolved_durations) / len(resolved_durations), 1) if resolved_durations else 0.0
    open_count = sum(
        status_counts.get(status.value, 0)
        for status in (ComplaintStatus.NEW, ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS)
    )
    return {
        "total_complaints": len(complaints),
        "open_complaints": open_count,
        "resolved_complaints": status_counts.get(ComplaintStatus.RESOLVED.value, 0)
        + status_counts.get(ComplaintStatus.CLOSED.value, 0),
        "escalated_complaints": escalated_count,
        "average_resolution_hours": average_resolution_hours,
        "status_counts": dict(status_counts),
        "department_summary": department_summary,
        "recent_complaints": complaints[:8],
    }


def user_metrics(db: Session) -> dict:
    users = db.execute(select(User)).scalars().all()
    departments = db.execute(select(Department).order_by(Department.name)).scalars().all()
    role_counts = Counter(user.role.value for user in users)
    return {
        "total_users": len(users),
        "active_users": sum(1 for user in users if user.is_active),
        "role_counts": dict(role_counts),
        "departments": departments,
    }


def citizen_dashboard_metrics(complaints: list[Complaint]) -> dict:
    status_counts = Counter(complaint.status.value for complaint in complaints)
    return {
        "total": len(complaints),
        "open": sum(
            status_counts.get(status.value, 0)
            for status in (ComplaintStatus.NEW, ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS)
        ),
        "resolved": status_counts.get(ComplaintStatus.RESOLVED.value, 0)
        + status_counts.get(ComplaintStatus.CLOSED.value, 0),
        "escalated": sum(1 for complaint in complaints if complaint.escalation_level > 0),
    }


def officer_dashboard_metrics(complaints: list[Complaint], user: User) -> dict:
    assigned_to_me = [complaint for complaint in complaints if complaint.assigned_officer_id == user.id]
    queue = [
        complaint
        for complaint in complaints
        if complaint.status in {ComplaintStatus.NEW, ComplaintStatus.ASSIGNED, ComplaintStatus.IN_PROGRESS}
    ]
    return {
        "department_total": len(complaints),
        "assigned_to_me": len(assigned_to_me),
        "queue_total": len(queue),
        "critical_open": sum(1 for complaint in queue if complaint.priority.value == "Critical"),
    }


def now_utc() -> datetime:
    return datetime.utcnow()
