"""
Seed data generator.
Produces:
  - 11 projects (as per assessment)
  - 5,500 seats across 5 floors × 10 zones
  - 5,000 employees
  - ~4,350 active seat allocations
  - ~100 reserved seats, ~50 maintenance
  - 50 employees with no seat (pending allocation)

Run: python -m app.utils.seed_data
"""
import random
from datetime import date, timedelta
from sqlalchemy.orm import Session

from ..database import SessionLocal, create_tables
from ..models.project import Project, ProjectStatus
from ..models.employee import Employee, EmployeeStatus
from ..models.seat import Seat, SeatStatus
from ..models.seat_allocation import SeatAllocation, AllocationStatus
from ..models.user import User
from ..dependencies import get_password_hash

# ── Constants ────────────────────────────────────────────────────────────────

PROJECTS = [
    {"name": "Indigo",    "manager_name": "Arjun Sharma",   "description": "Core platform team"},
    {"name": "Indreed",   "manager_name": "Priya Patel",    "description": "Recruitment automation"},
    {"name": "Mydreed",   "manager_name": "Rohan Verma",    "description": "Employee self-service"},
    {"name": "Preed",     "manager_name": "Kavita Nair",    "description": "Pre-hiring pipeline"},
    {"name": "Serfy",     "manager_name": "Aditya Gupta",   "description": "Service delivery platform"},
    {"name": "Oreed",     "manager_name": "Sneha Joshi",    "description": "Operations intelligence"},
    {"name": "Bedegreed", "manager_name": "Vikram Singh",   "description": "Learning & development"},
    {"name": "Opreed",    "manager_name": "Meera Reddy",    "description": "Ops automation"},
    {"name": "Serry",     "manager_name": "Kiran Kumar",    "description": "Support & resolution"},
    {"name": "Kaary",     "manager_name": "Ananya Das",     "description": "Workforce planning"},
    {"name": "Mered",     "manager_name": "Rahul Mehta",    "description": "Metrics & reporting"},
]

FLOORS = [1, 2, 3, 4, 5]
ZONES = list("ABCDEFGHIJ")   # 10 zones per floor
BAYS_PER_ZONE = 11           # Bay-1 to Bay-11
SEATS_PER_BAY = 10           # 10 seats per bay → 5 × 10 × 11 × 10 = 5,500 seats

DEPARTMENTS = [
    "Engineering", "Product", "Design", "Data Science", "DevOps",
    "QA", "HR", "Finance", "Marketing", "Operations", "Legal", "Security",
]

ROLES = [
    "Software Engineer", "Senior Software Engineer", "Staff Engineer", "Principal Engineer",
    "Product Manager", "Senior Product Manager", "UX Designer", "Data Scientist",
    "ML Engineer", "DevOps Engineer", "QA Engineer", "HR Manager",
    "Finance Analyst", "Marketing Manager", "Operations Lead", "Security Engineer",
    "Tech Lead", "Engineering Manager", "Director", "VP",
]

FIRST_NAMES = [
    "Aarav", "Aditya", "Akash", "Amit", "Ananya", "Anjali", "Arjun", "Aryan",
    "Ayesha", "Deepak", "Divya", "Gaurav", "Ishaan", "Kavita", "Kiran", "Komal",
    "Manish", "Meera", "Mohit", "Neeraj", "Neha", "Nikhil", "Pallavi", "Pooja",
    "Priya", "Rahul", "Raj", "Rajesh", "Riya", "Rohan", "Rohit", "Sandhya",
    "Sanjay", "Sara", "Shweta", "Sneha", "Suresh", "Swati", "Tanvi", "Varun",
    "Vikram", "Vinod", "Vishal", "Yash", "Zara", "Harsh", "Himanshu", "Kriti",
    "Lakshmi", "Mahesh",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Gupta", "Singh", "Kumar", "Nair", "Reddy",
    "Mehta", "Joshi", "Das", "Pillai", "Rao", "Iyer", "Menon", "Tiwari",
    "Mishra", "Pandey", "Banerjee", "Chatterjee", "Bose", "Roy", "Shah", "Modi",
    "Desai", "Kulkarni", "Jain", "Aggarwal", "Kapoor", "Malhotra",
]


# ── Generator functions ──────────────────────────────────────────────────────

def generate_seats() -> list[Seat]:
    seats = []
    seat_idx = 1
    for floor in FLOORS:
        for zone in ZONES:
            for bay_num in range(1, BAYS_PER_ZONE + 1):
                bay_name = f"Bay-{bay_num}"
                for seat_num in range(1, SEATS_PER_BAY + 1):
                    seat_number = f"{zone}{bay_num}-{seat_num:02d}"
                    seats.append(Seat(
                        floor=floor,
                        zone=zone,
                        bay=bay_name,
                        seat_number=seat_number,
                        status=SeatStatus.AVAILABLE,
                    ))
                    seat_idx += 1
    return seats  # 5,500 total


def generate_projects() -> list[Project]:
    return [
        Project(
            name=p["name"],
            description=p["description"],
            manager_name=p["manager_name"],
            status=ProjectStatus.ACTIVE,
        )
        for p in PROJECTS
    ]


def generate_employees(project_ids: list[int], count: int = 5000) -> list[Employee]:
    employees = []
    used_emails: set[str] = set()

    random.seed(42)

    for i in range(1, count + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f"{first} {last}"

        # Unique email
        base_email = f"{first.lower()}.{last.lower()}{i}@ethara.ai"
        email = base_email
        while email in used_emails:
            email = f"{first.lower()}.{last.lower()}{i}_{random.randint(1, 9999)}@ethara.ai"
        used_emails.add(email)

        joining_date = date(2020, 1, 1) + timedelta(days=random.randint(0, 365 * 5))

        employees.append(Employee(
            employee_code=f"ETH-{i:05d}",
            name=name,
            email=email,
            department=random.choice(DEPARTMENTS),
            role=random.choice(ROLES),
            joining_date=joining_date,
            status=EmployeeStatus.ACTIVE,
            project_id=random.choice(project_ids),
        ))
    return employees


def generate_allocations(
    employees: list[Employee],
    seats: list[Seat],
    project_map: dict[str, int],  # name → id
) -> tuple[list[SeatAllocation], list[Seat]]:
    """
    Allocate seats to employees.
    - 50 employees get NO seat (pending allocation)
    - 100 seats marked RESERVED
    - 50 seats marked MAINTENANCE
    - Rest: occupied
    Returns (allocations, updated_seats)
    """
    random.seed(42)

    # Mark reserved and maintenance seats first
    available_seats = list(seats)
    random.shuffle(available_seats)

    reserved_seats = available_seats[:100]
    maintenance_seats = available_seats[100:150]
    allocatable_seats = available_seats[150:]

    for s in reserved_seats:
        s.status = SeatStatus.RESERVED
    for s in maintenance_seats:
        s.status = SeatStatus.MAINTENANCE

    # 50 employees pending allocation
    pending_indices = set(random.sample(range(len(employees)), 50))
    allocations = []

    alloc_idx = 0
    for emp_idx, emp in enumerate(employees):
        if emp_idx in pending_indices:
            continue
        if alloc_idx >= len(allocatable_seats):
            break

        seat = allocatable_seats[alloc_idx]
        seat.status = SeatStatus.OCCUPIED
        alloc_idx += 1

        alloc_date = emp.joining_date + timedelta(days=random.randint(0, 14))

        allocations.append(SeatAllocation(
            employee_id=emp.id,
            seat_id=seat.id,
            project_id=emp.project_id,
            allocation_status=AllocationStatus.ACTIVE,
            allocation_date=alloc_date,
        ))

    return allocations, seats


# ── Main seed function ────────────────────────────────────────────────────────

def seed_database(db: Session, verbose: bool = True) -> dict:
    def log(msg):
        if verbose:
            print(msg)

    # Seed default user accounts (admin/adminpassword, hr/hrpassword)
    existing_admin = db.query(User).filter(User.username == "admin").first()
    if not existing_admin:
        log("Seeding default admin account...")
        admin_user = User(
            username="admin",
            email="admin@ethara.ai",
            hashed_password=get_password_hash("adminpassword"),
            is_admin=True,
        )
        db.add(admin_user)
        db.commit()

    existing_hr = db.query(User).filter(User.username == "hr").first()
    if not existing_hr:
        log("Seeding default hr account...")
        hr_user = User(
            username="hr",
            email="hr@ethara.ai",
            hashed_password=get_password_hash("hrpassword"),
            is_admin=False,
        )
        db.add(hr_user)
        db.commit()

    # Check if already seeded
    existing = db.query(Project).count()
    if existing > 0:
        log("Database already seeded. Skipping.")
        return {"status": "already_seeded"}

    log("Seeding projects...")
    projects = generate_projects()
    for p in projects:
        db.add(p)
    db.commit()
    for p in projects:
        db.refresh(p)
    project_ids = [p.id for p in projects]
    log(f"  ✓ {len(projects)} projects created")

    log("Seeding seats (5,500)...")
    seats = generate_seats()
    db.bulk_save_objects(seats)
    db.commit()
    # Re-query to get IDs
    seats = db.query(Seat).all()
    log(f"  ✓ {len(seats)} seats created")

    log("Seeding employees (5,000)...")
    employees = generate_employees(project_ids, count=5000)
    db.bulk_save_objects(employees)
    db.commit()
    employees = db.query(Employee).all()
    log(f"  ✓ {len(employees)} employees created")

    log("Generating seat allocations...")
    allocations, updated_seats = generate_allocations(employees, seats, {})

    # Update seat statuses
    for seat in updated_seats:
        db.add(seat)
    db.commit()

    db.bulk_save_objects(allocations)
    db.commit()

    reserved_count = sum(1 for s in updated_seats if s.status == SeatStatus.RESERVED)
    maintenance_count = sum(1 for s in updated_seats if s.status == SeatStatus.MAINTENANCE)
    occupied_count = sum(1 for s in updated_seats if s.status == SeatStatus.OCCUPIED)
    available_count = sum(1 for s in updated_seats if s.status == SeatStatus.AVAILABLE)

    log(f"  ✓ {len(allocations)} allocations created")
    log(f"  ✓ Seat status breakdown:")
    log(f"     Occupied:    {occupied_count}")
    log(f"     Available:   {available_count}")
    log(f"     Reserved:    {reserved_count}")
    log(f"     Maintenance: {maintenance_count}")
    log("Seeding complete!")

    return {
        "status": "success",
        "projects": len(projects),
        "seats": len(seats),
        "employees": len(employees),
        "allocations": len(allocations),
        "reserved_seats": reserved_count,
        "maintenance_seats": maintenance_count,
    }


if __name__ == "__main__":
    create_tables()
    db = SessionLocal()
    try:
        result = seed_database(db, verbose=True)
        print(result)
    finally:
        db.close()
