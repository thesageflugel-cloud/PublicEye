# System Schematics

## 1. System Architecture Diagram

```mermaid
flowchart LR
    Citizen["Citizen Portal"] --> Web["FastAPI Web Layer"]
    Officer["Officer Portal"] --> Web
    Admin["Admin Console"] --> Web
    Web --> Auth["Session Auth + RBAC"]
    Web --> ComplaintSvc["Complaint Workflow Service"]
    Web --> Analytics["Analytics Service"]
    ComplaintSvc --> DB[(SQLite Database)]
    Analytics --> DB
    Web --> Uploads["Evidence Storage"]
```

## 2. Complaint Workflow

```mermaid
flowchart LR
    New["New"] --> Assigned["Assigned"]
    Assigned --> InProgress["In Progress"]
    Assigned --> Resolved["Resolved"]
    InProgress --> Resolved
    Resolved --> Closed["Closed"]
    Resolved --> InProgress
```

## 3. Data Flow Diagram

```mermaid
flowchart TD
    Citizen["Citizen"] -->|"Complaint Form + Evidence"| PublicEye["PublicEye System"]
    Officer["Officer"] -->|"Progress Updates"| PublicEye
    Admin["Administrator"] -->|"Assignments + Monitoring"| PublicEye
    PublicEye -->|"Complaint Records"| ComplaintDB[(Complaint Database)]
    PublicEye -->|"Uploaded Images"| FileStore[(File Storage)]
    PublicEye -->|"Status and Dashboard Views"| Citizen
    PublicEye -->|"Department Queue"| Officer
    PublicEye -->|"Analytics and Escalations"| Admin
```

## 4. ER Diagram

```mermaid
erDiagram
    DEPARTMENTS ||--o{ USERS : contains
    USERS ||--o{ COMPLAINTS : creates
    USERS ||--o{ COMPLAINTS : assigned_to
    DEPARTMENTS ||--o{ COMPLAINTS : owns
    COMPLAINTS ||--o{ COMPLAINT_UPDATES : has
    USERS ||--o{ COMPLAINT_UPDATES : writes

    DEPARTMENTS {
        int id PK
        string name
        string description
    }

    USERS {
        int id PK
        string full_name
        string email
        string role
        int department_id FK
        bool is_active
    }

    COMPLAINTS {
        int id PK
        string reference_code
        string title
        string category
        string priority
        string status
        string location_text
        int citizen_id FK
        int department_id FK
        int assigned_officer_id FK
        int escalation_level
    }

    COMPLAINT_UPDATES {
        int id PK
        int complaint_id FK
        int actor_id FK
        string update_type
        string message
        string previous_status
        string new_status
    }
```

## 5. Sequence Diagram for Complaint Handling

```mermaid
sequenceDiagram
    participant C as Citizen
    participant W as Web App
    participant DB as Database
    participant A as Admin
    participant O as Officer

    C->>W: Submit complaint with details and image
    W->>DB: Save complaint and initial activity
    A->>W: Assign complaint to department/officer
    W->>DB: Update owner and status to Assigned
    O->>W: Mark In Progress and add note
    W->>DB: Save workflow update
    O->>W: Mark Resolved with proof
    W->>DB: Store proof and resolved timestamp
    A->>W: Close complaint
    W->>DB: Finalize workflow as Closed
```

## 6. Deployment Schematic

```mermaid
flowchart TD
    Browser["Browser"] --> FastAPI["FastAPI App"]
    FastAPI --> SQLite["SQLite DB"]
    FastAPI --> Uploads["Uploads Directory"]
```
