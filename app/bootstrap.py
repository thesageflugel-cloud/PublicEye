from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Complaint, ComplaintStatus, Department, PriorityLevel, RoleEnum, User
from app.security import hash_password
from app.services.complaints import add_update, calculate_due_at, generate_reference_code


DEFAULT_DEPARTMENTS = [
    ("Road Maintenance", "Handles potholes, road damage, and unsafe streets."),
    ("Sanitation", "Handles garbage overflow and public hygiene complaints."),
    ("Water & Drainage", "Handles leakage, drainage blockage, and sewer issues."),
    ("Electrical", "Handles faulty streetlights and civic electrical issues."),
    ("Public Safety", "Handles emergency hazards and unsafe public spaces."),
]


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_defaults(db)


def seed_defaults(db: Session) -> None:
    if db.execute(select(Department)).scalars().first() is None:
        for name, description in DEFAULT_DEPARTMENTS:
            db.add(Department(name=name, description=description))
        db.commit()

    departments = {department.name: department for department in db.execute(select(Department)).scalars().all()}

    if db.execute(select(User).where(User.role == RoleEnum.ADMIN)).scalars().first() is None:
        admin = User(
            full_name="System Administrator",
            email="admin@publiceye.local",
            phone="9000000001",
            password_hash=hash_password("Admin@123"),
            role=RoleEnum.ADMIN,
        )
        db.add(admin)
        db.commit()

    if db.execute(select(User).where(User.role == RoleEnum.OFFICER)).scalars().first() is None:
        officers = [
            User(
                full_name="Riya Sharma",
                email="roads.officer@publiceye.local",
                phone="9000000010",
                password_hash=hash_password("Officer@123"),
                role=RoleEnum.OFFICER,
                department_id=departments["Road Maintenance"].id,
            ),
            User(
                full_name="Akash Verma",
                email="sanitation.officer@publiceye.local",
                phone="9000000011",
                password_hash=hash_password("Officer@123"),
                role=RoleEnum.OFFICER,
                department_id=departments["Sanitation"].id,
            ),
            User(
                full_name="Nidhi Sahu",
                email="drainage.officer@publiceye.local",
                phone="9000000012",
                password_hash=hash_password("Officer@123"),
                role=RoleEnum.OFFICER,
                department_id=departments["Water & Drainage"].id,
            ),
        ]
        db.add_all(officers)
        db.commit()

    if db.execute(select(User).where(User.role == RoleEnum.CITIZEN)).scalars().first() is None:
        citizen = User(
            full_name="Demo Citizen",
            email="citizen@publiceye.local",
            phone="9000000100",
            password_hash=hash_password("Citizen@123"),
            role=RoleEnum.CITIZEN,
        )
        db.add(citizen)
        db.commit()

    if db.execute(select(Complaint)).scalars().first() is None:
        admin = db.execute(select(User).where(User.role == RoleEnum.ADMIN)).scalars().first()
        citizen = db.execute(select(User).where(User.role == RoleEnum.CITIZEN)).scalars().first()
        road_officer = db.execute(select(User).where(User.email == "roads.officer@publiceye.local")).scalars().first()
        sanitation_officer = db.execute(
            select(User).where(User.email == "sanitation.officer@publiceye.local")
        ).scalars().first()

        complaint_1 = Complaint(
            reference_code=generate_reference_code(),
            title="Large pothole near college gate",
            description="A deep pothole has formed near the main gate and is causing traffic and safety issues.",
            category="Road Damage",
            priority=PriorityLevel.HIGH,
            status=ComplaintStatus.IN_PROGRESS,
            location_text="Main Gate Road, Sector 5",
            ward="Ward 12",
            citizen_id=citizen.id,
            department_id=departments["Road Maintenance"].id,
            assigned_officer_id=road_officer.id,
            due_at=calculate_due_at(PriorityLevel.HIGH),
        )
        complaint_2 = Complaint(
            reference_code=generate_reference_code(),
            title="Garbage collection skipped for 3 days",
            description="Garbage bins near the market are overflowing and attracting stray animals.",
            category="Garbage Overflow",
            priority=PriorityLevel.MEDIUM,
            status=ComplaintStatus.RESOLVED,
            location_text="City Market Block A",
            ward="Ward 8",
            citizen_id=citizen.id,
            department_id=departments["Sanitation"].id,
            assigned_officer_id=sanitation_officer.id,
            due_at=datetime.utcnow() - timedelta(hours=12),
            resolved_at=datetime.utcnow() - timedelta(hours=4),
        )
        complaint_3 = Complaint(
            reference_code=generate_reference_code(),
            title="Blocked roadside drain causing waterlogging",
            description="Drain beside the bus stand is blocked and water is spilling onto the road.",
            category="Drainage Blockage",
            priority=PriorityLevel.CRITICAL,
            status=ComplaintStatus.NEW,
            location_text="Bus Stand Road",
            ward="Ward 2",
            citizen_id=citizen.id,
            department_id=departments["Water & Drainage"].id,
            due_at=datetime.utcnow() - timedelta(hours=6),
        )
        db.add_all([complaint_1, complaint_2, complaint_3])
        db.commit()

        add_update(db, complaint_1, citizen, "created", "Complaint submitted by citizen.")
        add_update(
            db,
            complaint_1,
            admin,
            "assignment",
            "Complaint assigned to Road Maintenance team.",
            previous_status=ComplaintStatus.NEW.value,
            new_status=ComplaintStatus.ASSIGNED.value,
        )
        add_update(
            db,
            complaint_1,
            road_officer,
            "status",
            "Site inspected and repair work has started.",
            previous_status=ComplaintStatus.ASSIGNED.value,
            new_status=ComplaintStatus.IN_PROGRESS.value,
        )
        add_update(db, complaint_2, citizen, "created", "Complaint submitted by citizen.")
        add_update(
            db,
            complaint_2,
            sanitation_officer,
            "status",
            "Garbage collected and area sanitized.",
            previous_status=ComplaintStatus.IN_PROGRESS.value,
            new_status=ComplaintStatus.RESOLVED.value,
        )
        add_update(db, complaint_3, citizen, "created", "Complaint submitted by citizen.")
        db.commit()
