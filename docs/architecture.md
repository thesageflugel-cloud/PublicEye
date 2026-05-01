# Architecture

## High-Level Architecture

PublicEye is implemented as a layered web application:

- Presentation Layer: Jinja-rendered HTML pages and light JavaScript for interactivity.
- Application Layer: FastAPI route handlers coordinate workflows, validation, and authorization.
- Domain Services: Complaint workflow logic and analytics aggregation.
- Data Layer: SQLAlchemy ORM with SQLite for users, departments, complaints, and updates.
- File Storage: Local uploads directory for evidence and proof images.

## Components

### 1. Web Layer

- Handles citizen registration and login
- Serves dashboards for all roles
- Accepts complaint forms and workflow actions

### 2. Security Layer

- Password hashing using PBKDF2-SHA256
- Session-based authentication
- Role-based authorization checks for citizen, officer, and admin actions

### 3. Complaint Service

- Generates complaint reference numbers
- Calculates due dates from SLA policy
- Validates status transitions
- Tracks escalation level for overdue open complaints

### 4. Analytics Service

- Aggregates complaint counts by status
- Computes department performance
- Calculates average resolution time
- Highlights escalated complaint volume

### 5. Persistence Layer

- `users` table for citizen, officer, and admin accounts
- `departments` table for municipal ownership
- `complaints` table for issue lifecycle data
- `complaint_updates` table for timeline and audit trail

## Why This Architecture Works for a Major Project

- Simple enough to run locally and demonstrate easily
- Structured enough to discuss production design decisions
- Extensible toward APIs, notifications, cloud deployment, and reporting pipelines
