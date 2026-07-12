"""
SeatRepository — Single Responsibility: all seat and allocation DB queries.
Handles proximity scoring for the allocation algorithm.
"""
from typing import Optional, List, Tuple
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_
from .base import BaseRepository
from ..models.seat import Seat, SeatStatus
from ..models.seat_allocation import SeatAllocation, AllocationStatus
from ..models.employee import Employee


class SeatRepository(BaseRepository[Seat]):

    def __init__(self, db: Session):
        super().__init__(Seat, db)

    # ── Seat lookups ────────────────────────────────────────────────────────

    def count(self, status: Optional[SeatStatus] = None) -> int:  # type: ignore[override]
        """Count seats, optionally filtered by status. Accepts SeatStatus enum or string."""
        q = self.db.query(Seat)
        if status is not None:
            if isinstance(status, str):
                # Normalise to uppercase to match Neon enum values
                status = SeatStatus(status.upper())
            q = q.filter(Seat.status == status)
        return q.count()

    def get_by_location(self, floor: int, zone: str, bay: str, seat_number: str) -> Optional[Seat]:
        return (
            self.db.query(Seat)
            .filter(
                Seat.floor == floor,
                func.upper(Seat.zone) == zone.upper(),
                Seat.bay == bay,
                Seat.seat_number == seat_number,
            )
            .first()
        )

    def get_with_allocation(self, seat_id: int) -> Optional[Seat]:
        return (
            self.db.query(Seat)
            .options(joinedload(Seat.allocations))
            .filter(Seat.id == seat_id)
            .first()
        )

    # ── Filtered search ─────────────────────────────────────────────────────

    def search(
        self,
        floor: Optional[int] = None,
        zone: Optional[str] = None,
        status: Optional[SeatStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Seat], int]:
        q = self.db.query(Seat)
        if floor is not None:
            q = q.filter(Seat.floor == floor)
        if zone:
            q = q.filter(func.upper(Seat.zone) == zone.upper())
        if status:
            q = q.filter(Seat.status == status)
        total = q.count()
        seats = q.order_by(Seat.floor, Seat.zone, Seat.seat_number).offset(skip).limit(limit).all()
        return seats, total

    def get_available(self, floor: Optional[int] = None, zone: Optional[str] = None) -> List[Seat]:
        q = self.db.query(Seat).filter(Seat.status == SeatStatus.AVAILABLE)
        if floor is not None:
            q = q.filter(Seat.floor == floor)
        if zone:
            q = q.filter(func.upper(Seat.zone) == zone.upper())
        return q.order_by(Seat.floor, Seat.zone, Seat.seat_number).all()

    # ── Allocation operations ────────────────────────────────────────────────

    def get_active_allocation_for_seat(self, seat_id: int) -> Optional[SeatAllocation]:
        return (
            self.db.query(SeatAllocation)
            .filter(
                SeatAllocation.seat_id == seat_id,
                SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
            )
            .first()
        )

    def get_active_allocation_for_employee(self, employee_id: int) -> Optional[SeatAllocation]:
        return (
            self.db.query(SeatAllocation)
            .filter(
                SeatAllocation.employee_id == employee_id,
                SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
            )
            .first()
        )

    def create_allocation(
        self,
        employee_id: int,
        seat_id: int,
        project_id: Optional[int],
    ) -> SeatAllocation:
        allocation = SeatAllocation(
            employee_id=employee_id,
            seat_id=seat_id,
            project_id=project_id,
            allocation_status=AllocationStatus.ACTIVE,
            allocation_date=date.today(),
        )
        self.db.add(allocation)
        # Update seat status
        seat = self.get(seat_id)
        if seat:
            seat.status = SeatStatus.OCCUPIED
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    def release_allocation(self, allocation: SeatAllocation) -> SeatAllocation:
        allocation.allocation_status = AllocationStatus.RELEASED
        allocation.released_date = date.today()
        seat = self.get(allocation.seat_id)
        if seat:
            seat.status = SeatStatus.AVAILABLE
        self.db.commit()
        self.db.refresh(allocation)
        return allocation

    # ── Dashboard aggregations ───────────────────────────────────────────────

    def count_by_status(self) -> dict:
        rows = (
            self.db.query(Seat.status, func.count(Seat.id))
            .group_by(Seat.status)
            .all()
        )
        # Normalize to the string value of the enum (e.g. "occupied" not "SeatStatus.OCCUPIED")
        result = {}
        for status, count in rows:
            key = status.value if hasattr(status, "value") else str(status)
            result[key] = count
        return result

    def floor_utilization(self) -> List[dict]:
        floors = (
            self.db.query(Seat.floor)
            .distinct()
            .order_by(Seat.floor)
            .all()
        )
        result = []
        for (floor,) in floors:
            counts = (
                self.db.query(Seat.status, func.count(Seat.id))
                .filter(Seat.floor == floor)
                .group_by(Seat.status)
                .all()
            )
            count_map = {
                (s.value if hasattr(s, "value") else str(s)).upper(): c
                for s, c in counts
            }
            total = sum(count_map.values())
            occupied = count_map.get("OCCUPIED", 0)
            result.append({
                "floor": floor,
                "total_seats": total,
                "occupied": occupied,
                "available": count_map.get("AVAILABLE", 0),
                "reserved": count_map.get("RESERVED", 0),
                "maintenance": count_map.get("MAINTENANCE", 0),
                "occupancy_rate": round(occupied / total * 100, 1) if total else 0.0,
            })
        return result

    # ── Proximity scoring ────────────────────────────────────────────────────

    def get_team_zones(self, project_id: int) -> dict:
        """
        Returns the most common floor and zone occupied by a project's team.
        Used by the proximity allocation algorithm.
        """
        rows = (
            self.db.query(Seat.floor, Seat.zone, func.count(SeatAllocation.id).label("cnt"))
            .join(SeatAllocation, and_(
                SeatAllocation.seat_id == Seat.id,
                SeatAllocation.allocation_status == AllocationStatus.ACTIVE,
                SeatAllocation.project_id == project_id,
            ))
            .group_by(Seat.floor, Seat.zone)
            .order_by(func.count(SeatAllocation.id).desc())
            .limit(3)
            .all()
        )
        if not rows:
            return {}
        top = rows[0]
        return {"floor": top.floor, "zone": top.zone, "count": top.cnt}

    def find_seats_near_project(self, project_id: int, limit: int = 10) -> List[Seat]:
        """
        Returns available seats scored by proximity to project's existing team.
        Algorithm: same zone (+3) > same floor (+2) > any available (+0).
        """
        team_location = self.get_team_zones(project_id)
        available = self.get_available()

        if not available:
            return []

        if not team_location:
            # No team seated yet — return first available seats
            return available[:limit]

        preferred_floor = team_location.get("floor")
        preferred_zone = team_location.get("zone", "").upper()

        def score(seat: Seat) -> int:
            s = 0
            if seat.zone.upper() == preferred_zone:
                s += 3
            if seat.floor == preferred_floor:
                s += 2
            return s

        scored = sorted(available, key=score, reverse=True)
        return scored[:limit]
