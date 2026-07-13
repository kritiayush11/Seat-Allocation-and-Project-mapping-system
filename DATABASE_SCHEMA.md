# Database Schema — Ethara Seat Allocation System

**Database:** Neon PostgreSQL 16 (`ap-southeast-1`)  
**Schema created via:** SQLAlchemy `Base.metadata.create_all()`  
**Alembic:** Configured but not yet used for versioned migrations (empty `alembic_version` table)

---

## Entity Relationship Overview

```
users
  (no FK relationships — standalone admin accounts)

projects
  └── employees (project_id → projects.id)
  └── seat_allocations (project_id → projects.id)

employees
  └── seat_allocations (employee_id → employees.id)

seats
  └── seat_allocations (seat_id → seats.id)

chat_messages
  (no FK — keyed by session_id string for AI chat history)
```

---

## Tables

### `users`
Stores administrator accounts. No relation to employees.

| Column            | Type          | Nullable | Notes                        |
| ----------------- | ------------- | -------- | ---------------------------- |
| `id`              | INTEGER       | NOT NULL | Primary key, auto-increment  |
| `username`        | VARCHAR(50)   | NOT NULL | Unique                       |
| `email`           | VARCHAR(100)  | NOT NULL | Unique                       |
| `hashed_password` | VARCHAR(255)  | NOT NULL | bcrypt hash                  |
| `is_admin`        | BOOLEAN       | NOT NULL |                              |
| `created_at`      | TIMESTAMP     | NOT NULL |                              |
| `updated_at`      | TIMESTAMP     | nullable |                              |

**Indexes:** `ix_users_username` (unique), `ix_users_email` (unique), `ix_users_id`

---

### `projects`
Represents a business project that employees are assigned to.

| Column         | Type          | Nullable | Notes                       |
| -------------- | ------------- | -------- | --------------------------- |
| `id`           | INTEGER       | NOT NULL | Primary key, auto-increment |
| `name`         | VARCHAR(100)  | NOT NULL | Unique                      |
| `description`  | VARCHAR(500)  | nullable |                             |
| `manager_name` | VARCHAR(150)  | nullable |                             |
| `status`       | VARCHAR(8)    | NOT NULL | Enum: `projectstatus`       |
| `created_at`   | TIMESTAMP     | NOT NULL |                             |
| `updated_at`   | TIMESTAMP     | nullable |                             |

**Indexes:** `ix_projects_name` (unique), `ix_projects_id`

---

### `employees`
Core entity. One employee belongs to one project (optional). Has at most one active seat allocation.

| Column          | Type          | Nullable | Notes                         |
| --------------- | ------------- | -------- | ----------------------------- |
| `id`            | INTEGER       | NOT NULL | Primary key, auto-increment   |
| `employee_code` | VARCHAR(20)   | NOT NULL | Unique — format: `ETH-XXXXX`  |
| `name`          | VARCHAR(150)  | NOT NULL |                               |
| `email`         | VARCHAR(200)  | NOT NULL | Unique                        |
| `department`    | VARCHAR(100)  | nullable |                               |
| `role`          | VARCHAR(100)  | nullable |                               |
| `joining_date`  | DATE          | NOT NULL |                               |
| `status`        | VARCHAR(10)   | NOT NULL | Enum: `employeestatus`        |
| `project_id`    | INTEGER       | nullable | FK → `projects.id`            |
| `created_at`    | TIMESTAMP     | NOT NULL |                               |
| `updated_at`    | TIMESTAMP     | nullable |                               |

**Indexes:** `ix_employees_email` (unique), `ix_employees_employee_code` (unique), `ix_employees_name`, `ix_employees_id`

---

### `seats`
Physical seats in the office. Identified by floor + zone + bay + seat_number.

| Column        | Type         | Nullable | Notes                               |
| ------------- | ------------ | -------- | ----------------------------------- |
| `id`          | INTEGER      | NOT NULL | Primary key, auto-increment         |
| `floor`       | INTEGER      | NOT NULL | Range: 1–20                         |
| `zone`        | VARCHAR(10)  | NOT NULL | e.g. `A`, `B`, `C`                  |
| `bay`         | VARCHAR(20)  | NOT NULL | e.g. `Bay-4`                        |
| `seat_number` | VARCHAR(30)  | NOT NULL | e.g. `B4-23`                        |
| `status`      | VARCHAR(11)  | NOT NULL | Enum: `seatstatus`                  |
| `created_at`  | TIMESTAMP    | NOT NULL |                                     |

**Unique constraint:** `uq_seat_location` on `(floor, zone, bay, seat_number)` — prevents duplicate seats  
**Indexes:** `ix_seats_floor`, `ix_seats_zone`, `ix_seats_seat_number`, `ix_seats_status`, `uq_seat_location` (unique)

---

### `seat_allocations`
Junction table between `employees` and `seats`. Records current and historical allocations.  
Business rule: only one `ACTIVE` allocation per employee and per seat at any time.

| Column              | Type         | Nullable | Notes                          |
| ------------------- | ------------ | -------- | ------------------------------ |
| `id`                | INTEGER      | NOT NULL | Primary key, auto-increment    |
| `employee_id`       | INTEGER      | NOT NULL | FK → `employees.id`            |
| `seat_id`           | INTEGER      | NOT NULL | FK → `seats.id`                |
| `project_id`        | INTEGER      | nullable | FK → `projects.id`             |
| `allocation_status` | VARCHAR(11)  | NOT NULL | Enum: `allocationstatus`       |
| `allocation_date`   | DATE         | NOT NULL |                                |
| `released_date`     | DATE         | nullable | Set when status → RELEASED     |
| `created_at`        | TIMESTAMP    | NOT NULL |                                |
| `updated_at`        | TIMESTAMP    | nullable |                                |

**Composite indexes (for fast active-allocation lookups):**
- `idx_active_employee_allocation` on `(employee_id, allocation_status)`
- `idx_active_seat_allocation` on `(seat_id, allocation_status)`

---

### `chat_messages`
Stores conversation history for the AI assistant, keyed by `session_id`.

| Column       | Type          | Nullable | Notes                                     |
| ------------ | ------------- | -------- | ----------------------------------------- |
| `id`         | INTEGER       | NOT NULL | Primary key, auto-increment               |
| `session_id` | VARCHAR(100)  | NOT NULL | Frontend-generated UUID per chat session  |
| `role`       | VARCHAR(50)   | NOT NULL | `user` or `assistant`                     |
| `content`    | TEXT          | NOT NULL | Message content                           |
| `created_at` | TIMESTAMP     | NOT NULL |                                           |

**Indexes:** `ix_chat_messages_session_id`, `ix_chat_messages_id`

---

## PostgreSQL Enum Types

All enums are UPPERCASE on Neon. The Python models match exactly.  
API responses serialise to lowercase. API inputs accept both cases.

```sql
employeestatus:    'ACTIVE', 'INACTIVE', 'ON_LEAVE', 'TERMINATED'
projectstatus:     'ACTIVE', 'INACTIVE', 'ARCHIVED'
seatstatus:        'AVAILABLE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE'
allocationstatus:  'ACTIVE', 'RELEASED', 'TRANSFERRED'
```

---

## Sequences (post-migration state)

| Sequence                       | Last Value | Next Insert |
| ------------------------------ | ---------- | ----------- |
| `employees_id_seq`             | 5003       | 5004        |
| `seats_id_seq`                 | 5502       | 5503        |
| `seat_allocations_id_seq`      | 4953       | 4954        |
| `projects_id_seq`              | 13         | 14          |
| `users_id_seq`                 | 10         | 11          |
| `chat_messages_id_seq`         | 4          | 5           |

> **Note:** Sequences were manually reset after bulk migration from SQLite using  
> `SELECT setval(pg_get_serial_sequence(table, 'id'), MAX(id))` to prevent `UniqueViolation` errors.

---

## Current Row Counts (live)

| Table               | Rows  |
| ------------------- | ----- |
| `employees`         | 5,003 |
| `seats`             | 5,502 |
| `seat_allocations`  | 4,953 |
| `projects`          | 13    |
| `users`             | 9     |
| `chat_messages`     | 4     |

---

## Notes

- **Schema creation:** `Base.metadata.create_all(bind=engine)` runs on every app startup (FastAPI lifespan hook). It is idempotent — only creates tables that don't exist yet.
- **No Alembic migrations applied yet** — the `alembic_version` table is present but empty. For future schema changes, generate and apply migrations with `alembic revision --autogenerate -m "description"` then `alembic upgrade head`.
- **Extra table:** `playing_with_neon` — Neon's default sample table, harmless.
