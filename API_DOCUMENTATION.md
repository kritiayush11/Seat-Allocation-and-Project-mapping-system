# API Documentation — Ethara Seat Allocation System

**Base URL (production):** `https://ethara-backend-xnma.onrender.com`  
**Base URL (local dev):** `http://localhost:8000`  
**Swagger UI:** `https://ethara-backend-xnma.onrender.com/docs`  
**ReDoc:** `https://ethara-backend-xnma.onrender.com/redoc`  
**OpenAPI JSON:** `https://ethara-backend-xnma.onrender.com/openapi.json`

---

## Authentication

All endpoints except `/health`, `/`, `/auth/login`, and `/auth/signup` require a **Bearer JWT token**.

```
Authorization: Bearer <token>
```

Tokens are obtained via `POST /auth/login` and expire after 60 minutes.

---

## Rate Limits

| Endpoint            | Limit       | Reason                         |
| ------------------- | ----------- | ------------------------------ |
| `POST /auth/login`  | 5 / minute  | Brute-force protection         |
| `POST /auth/signup` | 5 / minute  | Account spam prevention        |
| `GET /seats`        | 60 / minute | DB scraping protection         |
| `POST /seats/allocate` | 20 / minute | Seat-hoarding prevention    |
| `POST /ai/query`    | 10 / minute | LLM cost protection            |

Rate limits are per IP. Exceeding returns `429 Too Many Requests`.

---

## Endpoints

### Health

#### `GET /health`
Returns app health status. No auth required.

```json
{ "status": "healthy", "version": "1.0.0" }
```

#### `GET /`
```json
{ "message": "Ethara Seat Allocation API", "docs": "/docs", "version": "1.0.0" }
```

---

### Authentication

#### `POST /auth/signup`
Create a new administrator account.

**Body:**
```json
{
  "username": "admin",
  "email": "admin@ethara.ai",
  "password": "admin123"
}
```

**Response `201`:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@ethara.ai",
  "is_admin": true,
  "created_at": "2026-07-11T10:00:00"
}
```

**Errors:** `409` duplicate username/email, `422` validation error

---

#### `POST /auth/login`
Authenticate and receive a JWT token.

**Body:**
```json
{
  "username_or_email": "admin",
  "password": "admin123"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

**Errors:** `401` invalid credentials, `422` missing fields

---

#### `GET /auth/me`
Get currently authenticated user. Requires token.

**Response `200`:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@ethara.ai",
  "is_admin": true
}
```

---

### Employees

#### `POST /employees`
Create a new employee. `employee_code` is auto-generated as `ETH-XXXXX` if omitted.

**Body:**
```json
{
  "name": "Amit Kumar",
  "email": "amit@ethara.ai",
  "department": "Engineering",
  "role": "Software Engineer",
  "joining_date": "2026-07-01",
  "status": "active",
  "project_id": 3
}
```

**Response `201`:** Full `EmployeeResponse` with `id`, `employee_code`, `seat`, `project`.

**Errors:** `422` duplicate email, `404` project not found

---

#### `GET /employees`
List employees with optional filters.

**Query params:**

| Param         | Type    | Description                              |
| ------------- | ------- | ---------------------------------------- |
| `q`           | string  | Search by name, email, or employee code  |
| `project_id`  | int     | Filter by project                        |
| `status`      | string  | `active`, `inactive`, `on_leave`, `terminated` (case-insensitive) |
| `department`  | string  | Partial match                            |
| `has_seat`    | bool    | `true` = has seat, `false` = no seat     |
| `page`        | int     | Default 1                                |
| `page_size`   | int     | Default 50, max 200                      |

**Response `200`:**
```json
{
  "total": 5001,
  "page": 1,
  "page_size": 50,
  "employees": [ ... ]
}
```

---

#### `GET /employees/{id}`
Get a single employee including seat and project info.

**Response `200`:** Full `EmployeeResponse`  
**Errors:** `404` not found

---

#### `PUT /employees/{id}`
Update employee fields. All fields optional.

**Body:** Any subset of `name`, `email`, `department`, `role`, `status`, `project_id`, `joining_date`

**Errors:** `404` not found, `422` duplicate email

---

#### `DELETE /employees/{id}`
Soft-deactivate an employee (sets status to `INACTIVE`).

**Response `200`:** `{ "message": "Employee 5 deactivated successfully." }`

---

### Projects

#### `POST /projects`
```json
{ "name": "Indigo", "description": "AI platform", "manager_name": "Sara Ahmed" }
```
**Response `201`:** `ProjectResponse` with `employee_count` and `occupied_seats`

**Errors:** `422` duplicate name

---

#### `GET /projects`
| Param         | Type | Default | Description            |
| ------------- | ---- | ------- | ---------------------- |
| `active_only` | bool | `true`  | Only return ACTIVE     |

---

#### `GET /projects/{id}`
Returns project with `employee_count` and `occupied_seats`.

---

#### `PUT /projects/{id}`
Update project. Accepts `name`, `description`, `manager_name`, `status` (case-insensitive).

---

#### `GET /projects/{id}/employees`
Returns all employees assigned to the project.

---

### Seats

#### `POST /seats`
Create a new seat.
```json
{
  "floor": 3,
  "zone": "B",
  "bay": "Bay-4",
  "seat_number": "B4-23",
  "status": "available"
}
```
**Errors:** `422` duplicate location (floor+zone+bay+seat_number)

---

#### `GET /seats`
| Param       | Type   | Description                        |
| ----------- | ------ | ---------------------------------- |
| `floor`     | int    | Filter by floor (1–20)             |
| `zone`      | string | Filter by zone (case-insensitive)  |
| `status`    | string | `available`, `occupied`, `reserved`, `maintenance` |
| `page`      | int    | Default 1                          |
| `page_size` | int    | Default 50, max 200                |

---

#### `GET /seats/available`
Returns list of available seats, optionally filtered by `floor` and `zone`.

---

#### `GET /seats/suggest`
Suggest best seats for a new joiner using proximity scoring.

| Param        | Type | Required | Description             |
| ------------ | ---- | -------- | ----------------------- |
| `project_id` | int  | yes      | Project to score near   |
| `count`      | int  | no       | Number of suggestions (default 5, max 20) |

---

#### `GET /seats/{id}`
Get seat with current occupant details.

---

#### `PUT /seats/{id}`
Update seat fields. Accepts `status` (case-insensitive), `floor`, `zone`, `bay`, `seat_number`.

---

#### `POST /seats/allocate`
Allocate a seat to an employee.

```json
{
  "employee_id": 42,
  "seat_id": 100
}
```

If `seat_id` is omitted, the system auto-assigns the best seat by project proximity.

**Errors:**
- `404` employee or seat not found
- `409` employee already has a seat, or seat already occupied
- `403` seat is RESERVED or MAINTENANCE

---

#### `POST /seats/release`
Release an employee's current seat.
```json
{ "employee_id": 42 }
```

**Errors:** `400` no active allocation, `404` employee not found

---

### Dashboard

#### `GET /dashboard/summary`
Overall system statistics.

```json
{
  "total_employees": 5003,
  "active_employees": 4980,
  "total_seats": 5502,
  "occupied_seats": 4953,
  "available_seats": 449,
  "reserved_seats": 70,
  "maintenance_seats": 30,
  "pending_allocation": 50,
  "utilization_rate": 90.0
}
```

---

#### `GET /dashboard/project-utilization`
Per-project breakdown.
```json
[
  {
    "project_id": 1,
    "project_name": "Indigo",
    "total_employees": 450,
    "allocated_seats": 430,
    "unallocated_employees": 20
  }
]
```

---

#### `GET /dashboard/floor-utilization`
Per-floor occupancy.
```json
[
  {
    "floor": 1,
    "total_seats": 1100,
    "occupied": 990,
    "available": 90,
    "reserved": 15,
    "maintenance": 5,
    "occupancy_rate": 90.0
  }
]
```

---

### AI Assistant

#### `POST /ai/query`
Natural language query about seats, employees, and projects.

```json
{
  "query": "Where is Amit Kumar seated?",
  "session_id": "optional-uuid-for-memory"
}
```

**Response `200`:**
```json
{
  "answer": "Amit Kumar sits at Floor 3, Zone B, Bay-4, Seat B4-23. Project: Indigo.",
  "intent": "find_seat",
  "confidence": 0.9,
  "source": "groq",
  "session_id": "optional-uuid-for-memory"
}
```

**`source` values:** `groq`, `grok`, `openai`, `gemini`, `rule_based`  
**Min query length:** 3 characters  
**Rate limit:** 10/minute per IP

**Example queries:**
- `"Where is Amit seated?"`
- `"Show available seats on Floor 3"`
- `"How many seats are occupied for Project Indigo?"`
- `"Which project is sara@ethara.ai assigned to?"`
- `"Who is sitting near me? My email is john@ethara.ai"`

---

### Dev / Seed

#### `POST /seed`
Seed the database with synthetic data. Requires auth.

**Response `200`:** Summary of records created.

> ⚠️ Additive — does not clear existing data first.

---

## Common Error Responses

| Status | When                                                     |
| ------ | -------------------------------------------------------- |
| `401`  | Missing or invalid JWT token                             |
| `403`  | Seat is RESERVED or MAINTENANCE                          |
| `404`  | Resource not found                                       |
| `409`  | Duplicate / conflict (employee already seated, etc.)     |
| `422`  | Pydantic validation error (missing field, bad type, etc.)|
| `429`  | Rate limit exceeded                                      |

---

## Swagger UI

The interactive Swagger UI at `/docs` lets you try every endpoint in the browser.

To authenticate in Swagger:
1. Call `POST /auth/login` with your credentials
2. Copy the `access_token` from the response
3. Click **Authorize** (top right) and paste `<token>` (without `Bearer`)
