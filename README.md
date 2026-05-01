# PublicEye

PublicEye is a full-stack civic grievance monitoring and escalation system built from the supplied major project synopsis. It enables citizens to report infrastructure issues, municipal officers to manage resolution workflows, and administrators to monitor performance, accountability, and SLA breaches.

## Implemented Scope

- Citizen registration and login
- Role-based access for `Citizen`, `Officer`, and `Admin`
- Complaint submission with image upload and location data
- Complaint workflow: `New -> Assigned -> In Progress -> Resolved -> Closed`
- Complaint updates timeline and evidence trail
- Department assignment and officer mapping
- Admin analytics dashboard and staff account creation
- SLA-based escalation tracking
- SQLite-backed persistence with seeded demo users and sample complaints

## Stack

- Backend: FastAPI
- Templates: Jinja2
- Database: SQLite with SQLAlchemy ORM
- Frontend: Server-rendered HTML, CSS, and vanilla JavaScript
- Storage: Local file storage for uploaded evidence
- Testing: Pytest

## Project Directory

```text
PublicEye/
├── app/
│   ├── bootstrap.py
│   ├── config.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── routes/
│   │   └── web.py
│   ├── security.py
│   └── services/
│       ├── analytics.py
│       └── complaints.py
├── docs/
│   ├── architecture.md
│   ├── project-overview.md
│   ├── schematics.md
│   └── use-cases-and-advantages.md
├── static/
│   ├── css/app.css
│   └── js/app.js
├── storage/
│   └── uploads/
├── templates/
│   ├── base.html
│   ├── complaint_detail.html
│   ├── complaint_form.html
│   ├── dashboard_admin.html
│   ├── dashboard_citizen.html
│   ├── dashboard_officer.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── partials/flash.html
├── tests/
│   ├── test_security.py
│   └── test_workflow.py
├── .env.example
├── requirements.txt
└── run.py
```

## Demo Accounts

- Admin: `admin@publiceye.local` / `Admin@123`
- Officer: `roads.officer@publiceye.local` / `Officer@123`
- Citizen: `citizen@publiceye.local` / `Citizen@123`

## Run Locally

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Submission-Ready Notes

- The codebase is aligned to the synopsis theme `PublicEye – Smart Civic Grievance Monitoring & Escalation System`.
- The system schematics, use cases, advantages, and architecture explanation are included in the [`docs`](./docs) folder.
- You can extend this project later with email/SMS notifications, GIS layers, mobile apps, or cloud deployment.
