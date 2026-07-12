"""
AIAgent — Direct OpenAI SDK implementation (works with xAI/Grok, OpenAI, or any compatible API).

Architecture:
  - Uses openai SDK directly (no LangChain overhead)
  - Tool-calling loop: model decides which DB tools to call
  - Each tool queries Neon live and returns structured text
  - Chat history stored in DB (chat_messages table)
  - Priority: Grok (xAI free) → OpenAI → Gemini

Why not LangChain:
  - LangChain adds 5+ layers of abstraction over a simple API call
  - Version conflicts between langchain/langchain-core/langchain-openai
  - Direct SDK is faster, debuggable, and more reliable
"""
import json
from typing import Optional, List
from sqlalchemy.orm import Session
from openai import OpenAI

from ..repositories.employee_repository import EmployeeRepository
from ..repositories.seat_repository import SeatRepository
from ..repositories.project_repository import ProjectRepository
from ..models.chat_message import ChatMessage
from ..schemas.ai_assistant import AIResponse
from ..config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are Ethara's AI Assistant for Seat Allocation and Project Mapping.
You have access to real-time office data through tools.
ALWAYS call the relevant tool(s) before answering any question about seats, employees, or projects.
Be concise and accurate. Do not make up data — only use what tools return."""


def _get_client_and_source() -> tuple[Optional[OpenAI], str]:
    """Return (OpenAI client, source_name) for the first configured provider."""
    if settings.GROK_API_KEY or settings.XAI_API_KEY:
        key = settings.GROK_API_KEY or settings.XAI_API_KEY
        return OpenAI(api_key=key, base_url="https://api.x.ai/v1"), "grok"
    if settings.OPENAI_API_KEY:
        return OpenAI(api_key=settings.OPENAI_API_KEY), "openai"
    if settings.GEMINI_API_KEY:
        # Gemini supports OpenAI-compatible endpoint
        return OpenAI(
            api_key=settings.GEMINI_API_KEY,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        ), "gemini"
    return None, "rule_based"


def _get_model(source: str) -> str:
    if source == "grok":
        return settings.GROK_MODEL      # grok-3-mini
    if source == "gemini":
        return "gemini-2.0-flash"
    return settings.OPENAI_MODEL        # gpt-4o


# ── Tool definitions (OpenAI function-calling format) ─────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_employee_seat",
            "description": "Get seat location and project for a specific employee by name or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_or_name": {
                        "type": "string",
                        "description": "Employee email (preferred) or full/partial name"
                    }
                },
                "required": ["email_or_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_seats",
            "description": "List seats filtered by floor, zone, or status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "floor": {"type": "integer", "description": "Floor number (1-20)"},
                    "zone":  {"type": "string",  "description": "Zone letter e.g. A, B, C"},
                    "status": {"type": "string", "description": "AVAILABLE, OCCUPIED, RESERVED, or MAINTENANCE"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_seat_utilization",
            "description": "Get total seat counts and occupancy rate across the entire office.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_projects",
            "description": "Find projects by name and return manager and status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Project name or keyword"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_neighbors",
            "description": "Find co-workers seated near a specific employee in the same zone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email_or_name": {
                        "type": "string",
                        "description": "Employee email or name"
                    }
                },
                "required": ["email_or_name"]
            }
        }
    },
]


class AIAgent:
    def __init__(self, db: Session, session_id: str):
        self.db = db
        self.session_id = session_id
        self.emp_repo  = EmployeeRepository(db)
        self.seat_repo = SeatRepository(db)
        self.proj_repo = ProjectRepository(db)

    # ── Tool implementations ──────────────────────────────────────────────────

    def _get_employee_seat(self, email_or_name: str) -> str:
        emp = None
        if "@" in email_or_name:
            emp = self.emp_repo.get_by_email(email_or_name)
        if not emp:
            results, _ = self.emp_repo.search(query=email_or_name, limit=1)
            if results:
                emp = results[0]
        if not emp:
            return f"No employee found matching '{email_or_name}'."

        emp = self.emp_repo.get_with_details(emp.id)
        alloc = self.emp_repo.get_active_allocation(emp.id)
        proj = emp.project.name if emp.project else "No Project"

        if not alloc or not alloc.seat:
            return f"{emp.name} is on Project {proj} but has no active seat allocation."

        s = alloc.seat
        return (
            f"{emp.name} ({emp.email}) sits at Floor {s.floor}, Zone {s.zone}, "
            f"Bay {s.bay}, Seat {s.seat_number}. Project: {proj}."
        )

    def _search_seats(self, floor=None, zone=None, status=None) -> str:
        from ..models.seat import SeatStatus
        seat_status = None
        if status:
            try:
                seat_status = SeatStatus(status.upper())
            except ValueError:
                pass
        seats, _ = self.seat_repo.search(floor=floor, zone=zone, status=seat_status, limit=15)
        if not seats:
            return "No seats found matching the specified criteria."
        lines = [
            f"Seat {s.id}: Floor {s.floor}, Zone {s.zone}, {s.bay}, #{s.seat_number} — {s.status.value}"
            for s in seats
        ]
        return "\n".join(lines)

    def _get_seat_utilization(self) -> str:
        total       = self.seat_repo.count()
        occupied    = self.seat_repo.count(status="OCCUPIED")
        available   = self.seat_repo.count(status="AVAILABLE")
        reserved    = self.seat_repo.count(status="RESERVED")
        maintenance = self.seat_repo.count(status="MAINTENANCE")
        rate = (occupied / total * 100) if total else 0
        return (
            f"Total: {total} | Occupied: {occupied} | Available: {available} | "
            f"Reserved: {reserved} | Maintenance: {maintenance} | "
            f"Occupancy rate: {rate:.1f}%"
        )

    def _search_projects(self, query: str) -> str:
        projects, _ = self.proj_repo.search(query=query, limit=5)
        if not projects:
            return f"No projects found matching '{query}'."
        return "\n".join(
            f"Project: {p.name} | Manager: {p.manager_name or 'N/A'} | Status: {p.status.value}"
            for p in projects
        )

    def _find_neighbors(self, email_or_name: str) -> str:
        emp = None
        if "@" in email_or_name:
            emp = self.emp_repo.get_by_email(email_or_name)
        if not emp:
            results, _ = self.emp_repo.search(query=email_or_name, limit=1)
            if results:
                emp = results[0]
        if not emp:
            return f"Employee '{email_or_name}' not found."

        alloc = self.emp_repo.get_active_allocation(emp.id)
        if not alloc or not alloc.seat:
            return f"{emp.name} has no active seat — can't find neighbors."

        seat = alloc.seat
        nearby, _ = self.seat_repo.search(floor=seat.floor, zone=seat.zone, limit=10)
        neighbors = []
        for s in nearby:
            a = self.seat_repo.get_active_allocation_for_seat(s.id)
            if a and a.employee_id != emp.id and a.employee:
                neighbors.append(a.employee.name)
        if not neighbors:
            return f"No neighbors found near {emp.name} in Zone {seat.zone}, Floor {seat.floor}."
        return f"Neighbors of {emp.name} on Floor {seat.floor}, Zone {seat.zone}: {', '.join(neighbors[:5])}."

    def _dispatch_tool(self, name: str, args: dict) -> str:
        """Route tool call to the correct implementation."""
        if name == "get_employee_seat":
            return self._get_employee_seat(**args)
        if name == "search_seats":
            return self._search_seats(**args)
        if name == "get_seat_utilization":
            return self._get_seat_utilization()
        if name == "search_projects":
            return self._search_projects(**args)
        if name == "find_neighbors":
            return self._find_neighbors(**args)
        return f"Unknown tool: {name}"

    # ── Chat history ──────────────────────────────────────────────────────────

    def _load_history(self) -> List[dict]:
        records = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == self.session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        return [{"role": r.role, "content": r.content} for r in records]

    def _save_message(self, role: str, content: str) -> None:
        self.db.add(ChatMessage(
            session_id=self.session_id,
            role=role,
            content=content,
        ))
        self.db.commit()

    # ── Main entry ────────────────────────────────────────────────────────────

    def run(self, query: str) -> AIResponse:
        client, source = _get_client_and_source()

        if client is None:
            return AIResponse(
                answer=(
                    "No AI API key is configured. "
                    "Set XAI_API_KEY (free at console.x.ai) in Render env vars to enable Grok."
                ),
                intent="unknown",
                confidence=0.0,
                source="rule_based",
                session_id=self.session_id,
            )

        model = _get_model(source)
        history = self._load_history()
        self._save_message("user", query)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": query})

        try:
            # Agentic tool-calling loop (max 5 rounds to prevent runaway)
            for _ in range(5):
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3,
                    max_tokens=600,
                )
                msg = response.choices[0].message

                # No tool calls — final answer
                if not msg.tool_calls:
                    answer = msg.content or "I couldn't generate a response."
                    self._save_message("assistant", answer)
                    return AIResponse(
                        answer=answer,
                        intent="ai_agent",
                        confidence=0.9,
                        source=source,
                        session_id=self.session_id,
                    )

                # Execute each tool call
                messages.append(msg)  # append assistant message with tool_calls
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    result = self._dispatch_tool(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })

            # Exceeded loop — return last content if available
            answer = "I was unable to complete the query in time. Please try rephrasing."
            return AIResponse(
                answer=answer,
                intent="ai_agent",
                confidence=0.3,
                source=source,
                session_id=self.session_id,
            )

        except Exception as e:
            return AIResponse(
                answer=f"AI error ({source}): {str(e)}",
                intent="unknown",
                confidence=0.0,
                source=source,
                session_id=self.session_id,
            )
