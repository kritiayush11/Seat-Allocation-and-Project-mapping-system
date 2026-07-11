"""
AIAssistantService — Single Responsibility: natural language query resolution.
Architecture:
  1. Rule-based IntentParser (always runs, free, deterministic)
  2. OpenAI GPT-4o fallback (optional, enabled when OPENAI_API_KEY is set)
"""
from typing import Optional
from sqlalchemy.orm import Session

from ..repositories.employee_repository import EmployeeRepository
from ..repositories.seat_repository import SeatRepository
from ..repositories.project_repository import ProjectRepository
from ..utils.intent_parser import IntentParser, ParsedIntent
from ..schemas.ai_assistant import AIResponse
from ..config import get_settings

settings = get_settings()


class AIAssistantService:

    def __init__(self, db: Session):
        self.emp_repo = EmployeeRepository(db)
        self.seat_repo = SeatRepository(db)
        self.proj_repo = ProjectRepository(db)
        self.parser = IntentParser()
        self.db = db

    def answer(self, query: str, session_id: Optional[str] = None) -> AIResponse:
        if session_id:
            if settings.GEMINI_API_KEY or settings.GROK_API_KEY or settings.XAI_API_KEY or settings.OPENAI_API_KEY:
                from .ai_agent import AIAgent
                agent = AIAgent(self.db, session_id)
                return agent.run(query)

        intent = self.parser.parse(query)

        if intent.intent == "find_seat":
            return self._handle_find_seat(intent)
        elif intent.intent == "find_project":
            return self._handle_find_project(intent)
        elif intent.intent == "available_seats":
            return self._handle_available_seats(intent)
        elif intent.intent == "seat_utilization":
            return self._handle_utilization(intent)
        elif intent.intent == "allocate_seat":
            return self._handle_allocate_hint(intent)
        elif intent.intent == "find_neighbors":
            return self._handle_neighbors(intent)
        else:
            # Try OpenAI fallback if key is configured
            if settings.OPENAI_API_KEY:
                return self._openai_fallback(query)
            return AIResponse(
                answer=(
                    "I'm not sure how to answer that. Try asking things like:\n"
                    "• 'Where is Amit seated?'\n"
                    "• 'Which project is sara@ethara.ai assigned to?'\n"
                    "• 'Show available seats on Floor 3'\n"
                    "• 'How many seats are occupied for Project Indigo?'"
                ),
                intent="unknown",
                confidence=0.0,
                source="rule_based",
                session_id=session_id
            )

    # ── Intent handlers ──────────────────────────────────────────────────────

    def _handle_find_seat(self, intent: ParsedIntent) -> AIResponse:
        employee = self._resolve_employee(intent.entities)
        if not employee:
            return AIResponse(
                answer="I couldn't find that employee. Please provide a valid name or email.",
                intent="find_seat",
                source="rule_based",
            )

        allocation = self.emp_repo.get_active_allocation(employee.id)
        if not allocation or not allocation.seat:
            return AIResponse(
                answer=f"{employee.name} does not currently have a seat allocated.",
                intent="find_seat",
                data={"employee_id": employee.id, "employee_code": employee.employee_code},
                source="rule_based",
            )

        seat = allocation.seat
        proj_name = employee.project.name if employee.project else "No Project"
        answer = (
            f"{employee.name} is seated on Floor {seat.floor}, Zone {seat.zone}, "
            f"{seat.bay}, Seat {seat.seat_number}. "
            f"They are assigned to Project {proj_name}."
        )
        return AIResponse(
            answer=answer,
            intent="find_seat",
            confidence=0.95,
            source="rule_based",
            data={
                "employee_id": employee.id,
                "employee_code": employee.employee_code,
                "floor": seat.floor,
                "zone": seat.zone,
                "bay": seat.bay,
                "seat_number": seat.seat_number,
                "project": proj_name,
            },
        )

    def _handle_find_project(self, intent: ParsedIntent) -> AIResponse:
        employee = self._resolve_employee(intent.entities)
        if not employee:
            return AIResponse(
                answer="I couldn't find that employee.",
                intent="find_project",
                source="rule_based",
            )
        proj_name = employee.project.name if employee.project else "No Project assigned"
        return AIResponse(
            answer=f"{employee.name} (Code: {employee.employee_code}) is assigned to Project {proj_name}.",
            intent="find_project",
            confidence=0.95,
            source="rule_based",
            data={"employee_id": employee.id, "project": proj_name},
        )

    def _handle_available_seats(self, intent: ParsedIntent) -> AIResponse:
        floor = intent.entities.get("floor")
        zone = intent.entities.get("zone")
        seats = self.seat_repo.get_available(floor=floor, zone=zone)

        if not seats:
            location = f"Floor {floor}" if floor else ""
            location += f", Zone {zone}" if zone else ""
            return AIResponse(
                answer=f"No available seats found{' on ' + location.strip(', ') if location else ''}.",
                intent="available_seats",
                source="rule_based",
            )

        location_desc = ""
        if floor:
            location_desc += f" on Floor {floor}"
        if zone:
            location_desc += f", Zone {zone}"

        sample = seats[:5]
        seat_list = ", ".join(
            f"Floor {s.floor} Zone {s.zone} {s.bay} Seat {s.seat_number}" for s in sample
        )
        answer = (
            f"There are {len(seats)} available seats{location_desc}. "
            f"Sample seats: {seat_list}{'...' if len(seats) > 5 else ''}."
        )
        return AIResponse(
            answer=answer,
            intent="available_seats",
            confidence=0.9,
            source="rule_based",
            data={"count": len(seats), "floor": floor, "zone": zone},
        )

    def _handle_utilization(self, intent: ParsedIntent) -> AIResponse:
        project_name = intent.entities.get("project_name")
        floor = intent.entities.get("floor")

        if project_name:
            project = self.proj_repo.get_by_name(project_name)
            if not project:
                # fuzzy match attempt
                all_projects = self.proj_repo.get_all_active()
                matches = [p for p in all_projects if project_name.lower() in p.name.lower()]
                if matches:
                    project = matches[0]

            if not project:
                return AIResponse(
                    answer=f"Project '{project_name}' not found.",
                    intent="seat_utilization",
                    source="rule_based",
                )

            utils = self.proj_repo.get_utilization()
            proj_data = next((u for u in utils if u["project_id"] == project.id), None)
            if proj_data:
                return AIResponse(
                    answer=(
                        f"Project {project.name} has {proj_data['total_employees']} employees, "
                        f"{proj_data['allocated_seats']} seats occupied, "
                        f"{proj_data['unallocated_employees']} employees without seats."
                    ),
                    intent="seat_utilization",
                    confidence=0.9,
                    source="rule_based",
                    data=proj_data,
                )

        if floor:
            floor_data = self.seat_repo.floor_utilization()
            fdata = next((f for f in floor_data if f["floor"] == floor), None)
            if fdata:
                return AIResponse(
                    answer=(
                        f"Floor {floor} has {fdata['total_seats']} total seats. "
                        f"{fdata['occupied']} occupied ({fdata['occupancy_rate']}%), "
                        f"{fdata['available']} available, {fdata['reserved']} reserved."
                    ),
                    intent="seat_utilization",
                    confidence=0.9,
                    source="rule_based",
                    data=fdata,
                )

        return AIResponse(
            answer="Please specify a project name or floor number for utilization info.",
            intent="seat_utilization",
            source="rule_based",
        )

    def _handle_allocate_hint(self, intent: ParsedIntent) -> AIResponse:
        email = intent.entities.get("email")
        if email:
            emp = self.emp_repo.get_by_email(email)
            if emp:
                return AIResponse(
                    answer=(
                        f"To allocate a seat for {emp.name}, use the Seat Allocation page "
                        f"or call POST /seats/allocate with employee_id={emp.id}."
                    ),
                    intent="allocate_seat",
                    source="rule_based",
                    data={"employee_id": emp.id},
                )
        available_count = len(self.seat_repo.get_available())
        return AIResponse(
            answer=(
                f"There are {available_count} seats available. "
                "Go to the Seat Allocation page, search for the new employee, and click 'Allocate Seat'. "
                "The system will auto-suggest the best seat based on their project team location."
            ),
            intent="allocate_seat",
            source="rule_based",
        )

    def _handle_neighbors(self, intent: ParsedIntent) -> AIResponse:
        employee = self._resolve_employee(intent.entities)
        if not employee:
            return AIResponse(
                answer="Please provide your name or email to find neighbors.",
                intent="find_neighbors",
                source="rule_based",
            )
        allocation = self.emp_repo.get_active_allocation(employee.id)
        if not allocation or not allocation.seat:
            return AIResponse(
                answer=f"{employee.name} doesn't have an assigned seat yet.",
                intent="find_neighbors",
                source="rule_based",
            )
        seat = allocation.seat
        # Find seats in same zone and bay
        nearby, _ = self.seat_repo.search(floor=seat.floor, zone=seat.zone, limit=10)
        neighbors = []
        for s in nearby:
            active = self.seat_repo.get_active_allocation_for_seat(s.id)
            if active and active.employee_id != employee.id and active.employee:
                neighbors.append(active.employee.name)

        if neighbors:
            names = ", ".join(neighbors[:5])
            answer = f"Neighbors of {employee.name} on Floor {seat.floor}, Zone {seat.zone}: {names}."
        else:
            answer = f"No neighbors found near {employee.name} in Zone {seat.zone}, Floor {seat.floor}."

        return AIResponse(
            answer=answer,
            intent="find_neighbors",
            confidence=0.8,
            source="rule_based",
        )

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _resolve_employee(self, entities: dict):
        """Try email first, then name search."""
        email = entities.get("email")
        name = entities.get("name")

        if email:
            emp = self.emp_repo.get_by_email(email)
            if emp:
                # Eager load project and allocation
                return self.emp_repo.get_with_details(emp.id)

        if name:
            employees, _ = self.emp_repo.search(query=name, limit=1)
            if employees:
                return self.emp_repo.get_with_details(employees[0].id)

        return None

    def _openai_fallback(self, query: str) -> AIResponse:
        """Use OpenAI GPT-4o as fallback for unknown intents."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Build context from DB
            summary_data = f"System manages seat allocation for ~5000 Ethara employees."

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"{summary_data} "
                            "You are a helpful assistant for the Ethara Seat Allocation System. "
                            "Answer concisely based on the user's query about seats, employees, and projects."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
                max_tokens=200,
                temperature=0.3,
            )
            answer = response.choices[0].message.content.strip()
            return AIResponse(
                answer=answer,
                intent="openai_fallback",
                confidence=0.7,
                source="openai",
            )
        except Exception as e:
            return AIResponse(
                answer="I couldn't process that query. Please try rephrasing.",
                intent="unknown",
                source="rule_based",
            )
