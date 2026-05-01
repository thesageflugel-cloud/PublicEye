from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import APP_NAME, COMPLAINT_CATEGORIES, TEMPLATES_DIR
from app.database import get_db
from app.models import Complaint, ComplaintStatus, ComplaintUpdate, Department, PriorityLevel, RoleEnum, User
from app.security import consume_flashes, flash, hash_password, verify_password
from app.services.analytics import (
    citizen_dashboard_metrics,
    officer_dashboard_metrics,
    overall_metrics,
    user_metrics,
)
from app.services.complaints import (
    add_update,
    calculate_due_at,
    can_transition,
    complaint_visible_to,
    generate_reference_code,
    refresh_escalations,
    save_upload,
)


router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def render(request: Request, template_name: str, context: dict) -> HTMLResponse:
    base_context = {
        "request": request,
        "app_name": APP_NAME,
        "flashes": consume_flashes(request),
    }
    base_context.update(context)
    return templates.TemplateResponse(template_name, base_context)


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return int(stripped)


def get_current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        request.session.pop("user_id", None)
        return None
    return user


def require_user(request: Request, db: Session) -> User | None:
    user = get_current_user(request, db)
    if user is None:
        flash(request, "error", "Please log in to continue.")
        return None
    return user


def visible_complaints_for_user(db: Session, user: User) -> list[Complaint]:
    query = (
        select(Complaint)
        .options(
            joinedload(Complaint.citizen),
            joinedload(Complaint.department),
            joinedload(Complaint.assigned_officer),
        )
        .order_by(Complaint.created_at.desc())
    )
    complaints = db.execute(query).unique().scalars().all()
    if user.role == RoleEnum.ADMIN:
        return complaints
    if user.role == RoleEnum.CITIZEN:
        return [complaint for complaint in complaints if complaint.citizen_id == user.id]
    return [
        complaint
        for complaint in complaints
        if complaint.assigned_officer_id == user.id or complaint.department_id == user.department_id
    ]


def fetch_complaint_or_redirect(
    request: Request,
    db: Session,
    user: User,
    complaint_id: int,
) -> Complaint | RedirectResponse:
    complaint = db.execute(
        select(Complaint)
        .where(Complaint.id == complaint_id)
        .options(
            joinedload(Complaint.citizen),
            joinedload(Complaint.department),
            joinedload(Complaint.assigned_officer),
            joinedload(Complaint.updates).joinedload(ComplaintUpdate.actor),
        )
    ).unique().scalars().first()
    if complaint is None or not complaint_visible_to(user, complaint):
        flash(request, "error", "Complaint not found or access denied.")
        return redirect("/dashboard")
    return complaint


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return redirect("/dashboard")
    return render(request, "index.html", {"current_user": None})


@router.get("/health", response_class=JSONResponse)
def health_check():
    return JSONResponse({"status": "ok", "service": APP_NAME})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "login.html", {"current_user": get_current_user(request, db)})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.email == email.strip().lower())).scalars().first()
    if user is None or not verify_password(password, user.password_hash):
        flash(request, "error", "Invalid email or password.")
        return redirect("/login")
    request.session["user_id"] = user.id
    flash(request, "success", f"Welcome back, {user.full_name}.")
    return redirect("/dashboard")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "register.html", {"current_user": get_current_user(request, db)})


@router.post("/register")
async def register(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    normalized_email = email.strip().lower()
    if password != confirm_password:
        flash(request, "error", "Passwords do not match.")
        return redirect("/register")
    existing_user = db.execute(select(User).where(User.email == normalized_email)).scalars().first()
    if existing_user is not None:
        flash(request, "error", "An account with this email already exists.")
        return redirect("/register")
    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        phone=phone.strip() or None,
        password_hash=hash_password(password),
        role=RoleEnum.CITIZEN,
    )
    db.add(user)
    db.commit()
    flash(request, "success", "Registration successful. Please log in.")
    return redirect("/login")


@router.post("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)
    flash(request, "success", "You have been logged out.")
    return redirect("/login")


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    refresh_escalations(db)
    complaints = visible_complaints_for_user(db, user)
    departments = db.execute(select(Department).order_by(Department.name)).scalars().all()

    if user.role == RoleEnum.CITIZEN:
        metrics = citizen_dashboard_metrics(complaints)
        return render(
            request,
            "dashboard_citizen.html",
            {
                "current_user": user,
                "complaints": complaints,
                "metrics": metrics,
            },
        )

    if user.role == RoleEnum.OFFICER:
        metrics = officer_dashboard_metrics(complaints, user)
        officers = db.execute(
            select(User).where(User.role == RoleEnum.OFFICER, User.department_id == user.department_id)
        ).scalars().all()
        return render(
            request,
            "dashboard_officer.html",
            {
                "current_user": user,
                "complaints": complaints,
                "metrics": metrics,
                "departments": departments,
                "officers": officers,
            },
        )

    metrics = overall_metrics(db)
    users = user_metrics(db)
    officers = db.execute(select(User).where(User.role == RoleEnum.OFFICER).order_by(User.full_name)).scalars().all()
    return render(
        request,
        "dashboard_admin.html",
        {
            "current_user": user,
            "complaints": complaints,
            "metrics": metrics,
            "user_stats": users,
            "departments": departments,
            "officers": officers,
            "statuses": list(ComplaintStatus),
        },
    )


@router.get("/complaints/new", response_class=HTMLResponse)
def new_complaint_page(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    if user.role != RoleEnum.CITIZEN:
        flash(request, "error", "Only citizens can register complaints.")
        return redirect("/dashboard")
    departments = db.execute(select(Department).order_by(Department.name)).scalars().all()
    return render(
        request,
        "complaint_form.html",
        {
            "current_user": user,
            "departments": departments,
            "categories": COMPLAINT_CATEGORIES,
            "priorities": list(PriorityLevel),
        },
    )


@router.post("/complaints")
async def create_complaint(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    priority: PriorityLevel = Form(...),
    location_text: str = Form(...),
    ward: str = Form(""),
    department_id: str = Form(""),
    latitude: str = Form(""),
    longitude: str = Form(""),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    if user.role != RoleEnum.CITIZEN:
        flash(request, "error", "Only citizens can create complaints.")
        return redirect("/dashboard")
    try:
        image_path = save_upload(image, subfolder="complaints")
    except ValueError as error:
        flash(request, "error", str(error))
        return redirect("/complaints/new")

    complaint = Complaint(
        reference_code=generate_reference_code(),
        title=title.strip(),
        description=description.strip(),
        category=category.strip(),
        priority=priority,
        status=ComplaintStatus.NEW,
        location_text=location_text.strip(),
        ward=ward.strip() or None,
        latitude=Decimal(latitude) if latitude else None,
        longitude=Decimal(longitude) if longitude else None,
        image_path=image_path,
        citizen_id=user.id,
        department_id=optional_int(department_id),
        due_at=calculate_due_at(priority),
    )
    db.add(complaint)
    add_update(db, complaint, user, "created", "Complaint submitted with initial evidence.")
    db.commit()
    flash(request, "success", f"Complaint {complaint.reference_code} created successfully.")
    return redirect(f"/complaints/{complaint.id}")


@router.get("/complaints/{complaint_id}", response_class=HTMLResponse)
def complaint_detail(complaint_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    complaint = fetch_complaint_or_redirect(request, db, user, complaint_id)
    if isinstance(complaint, RedirectResponse):
        return complaint
    departments = db.execute(select(Department).order_by(Department.name)).scalars().all()
    officers = db.execute(select(User).where(User.role == RoleEnum.OFFICER).order_by(User.full_name)).scalars().all()
    return render(
        request,
        "complaint_detail.html",
        {
            "current_user": user,
            "complaint": complaint,
            "departments": departments,
            "officers": officers,
            "statuses": list(ComplaintStatus),
        },
    )


@router.post("/complaints/{complaint_id}/comment")
async def add_comment(
    complaint_id: int,
    request: Request,
    message: str = Form(...),
    attachment: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    complaint = fetch_complaint_or_redirect(request, db, user, complaint_id)
    if isinstance(complaint, RedirectResponse):
        return complaint
    try:
        attachment_path = save_upload(attachment, subfolder="updates")
    except ValueError as error:
        flash(request, "error", str(error))
        return redirect(f"/complaints/{complaint_id}")
    add_update(db, complaint, user, "comment", message.strip(), attachment_path=attachment_path)
    db.commit()
    flash(request, "success", "Update posted successfully.")
    return redirect(f"/complaints/{complaint_id}")


@router.post("/complaints/{complaint_id}/assign")
async def assign_complaint(
    complaint_id: int,
    request: Request,
    department_id: int = Form(...),
    officer_id: str = Form(""),
    message: str = Form("Complaint triaged and assigned."),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    if user.role != RoleEnum.ADMIN:
        flash(request, "error", "Only administrators can assign complaints.")
        return redirect(f"/complaints/{complaint_id}")
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        flash(request, "error", "Complaint not found.")
        return redirect("/dashboard")
    parsed_officer_id = optional_int(officer_id)
    officer = db.get(User, parsed_officer_id) if parsed_officer_id else None
    department = db.get(Department, department_id)
    previous_status = complaint.status
    complaint.department_id = department_id
    complaint.assigned_officer_id = parsed_officer_id
    complaint.status = ComplaintStatus.ASSIGNED
    add_update(
        db,
        complaint,
        user,
        "assignment",
        message.strip() or f"Complaint assigned to {department.name}.",
        previous_status=previous_status.value,
        new_status=ComplaintStatus.ASSIGNED.value,
    )
    if officer and officer.department_id != department_id:
        officer.department_id = department_id
    db.commit()
    flash(request, "success", "Complaint assigned successfully.")
    return redirect(f"/complaints/{complaint_id}")


@router.post("/complaints/{complaint_id}/status")
async def update_status(
    complaint_id: int,
    request: Request,
    new_status: ComplaintStatus = Form(...),
    message: str = Form(...),
    proof: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    complaint = fetch_complaint_or_redirect(request, db, user, complaint_id)
    if isinstance(complaint, RedirectResponse):
        return complaint
    if user.role == RoleEnum.CITIZEN:
        flash(request, "error", "Citizens cannot change complaint status.")
        return redirect(f"/complaints/{complaint_id}")
    if user.role == RoleEnum.OFFICER and complaint.department_id != user.department_id and complaint.assigned_officer_id != user.id:
        flash(request, "error", "You can update only department complaints assigned to your team.")
        return redirect(f"/complaints/{complaint_id}")
    if new_status != complaint.status and not can_transition(complaint.status, new_status):
        flash(request, "error", f"Invalid status transition from {complaint.status.value} to {new_status.value}.")
        return redirect(f"/complaints/{complaint_id}")
    try:
        proof_path = save_upload(proof, subfolder="proofs")
    except ValueError as error:
        flash(request, "error", str(error))
        return redirect(f"/complaints/{complaint_id}")

    previous_status = complaint.status
    complaint.status = new_status
    complaint.updated_at = datetime.utcnow()
    if new_status == ComplaintStatus.RESOLVED:
        complaint.resolved_at = datetime.utcnow()
        if proof_path:
            complaint.resolution_proof_path = proof_path
    if new_status == ComplaintStatus.CLOSED:
        complaint.closed_at = datetime.utcnow()
    if new_status == ComplaintStatus.IN_PROGRESS and complaint.assigned_officer_id is None:
        complaint.assigned_officer_id = user.id
    add_update(
        db,
        complaint,
        user,
        "status",
        message.strip(),
        previous_status=previous_status.value,
        new_status=new_status.value,
        attachment_path=proof_path,
    )
    db.commit()
    flash(request, "success", "Complaint status updated successfully.")
    return redirect(f"/complaints/{complaint_id}")


@router.post("/admin/users/create-officer")
async def create_staff_account(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    role: RoleEnum = Form(...),
    department_id: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    if user is None:
        return redirect("/login")
    if user.role != RoleEnum.ADMIN:
        flash(request, "error", "Only administrators can create staff accounts.")
        return redirect("/dashboard")
    normalized_email = email.strip().lower()
    if role == RoleEnum.CITIZEN:
        flash(request, "error", "Use public registration for citizen accounts.")
        return redirect("/dashboard")
    if db.execute(select(User).where(User.email == normalized_email)).scalars().first():
        flash(request, "error", "Email is already in use.")
        return redirect("/dashboard")
    account = User(
        full_name=full_name.strip(),
        email=normalized_email,
        phone=phone.strip() or None,
        password_hash=hash_password(password),
        role=role,
        department_id=optional_int(department_id) if role == RoleEnum.OFFICER else None,
    )
    db.add(account)
    db.commit()
    flash(request, "success", f"{role.value} account created successfully.")
    return redirect("/dashboard")
