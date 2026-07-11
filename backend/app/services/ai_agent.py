import uuid
from typing import List, Optional, Any
from sqlalchemy.orm import Session
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.agents import AgentExecutor, create_tool_calling_agent

# Import repositories
from ..repositories.employee_repository import EmployeeRepository
from ..repositories.seat_repository import SeatRepository
from ..repositories.project_repository import ProjectRepository
from ..models.chat_message import ChatMessage
from ..schemas.ai_assistant import AIResponse
from ..config import get_settings

settings = get_settings()


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, db: Session, session_id: str):
        self.db = db
        self.session_id = session_id

    @property
    def messages(self) -> List[BaseMessage]:
        records = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == self.session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        msgs = []
        for r in records:
            if r.role == "user":
                msgs.append(HumanMessage(content=r.content))
            else:
                msgs.append(AIMessage(content=r.content))
        return msgs

    def add_message(self, message: BaseMessage) -> None:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        db_msg = ChatMessage(
            session_id=self.session_id,
            role=role,
            content=message.content
        )
        self.db.add(db_msg)
        self.db.commit()

    def clear(self) -> None:
        self.db.query(ChatMessage).filter(ChatMessage.session_id == self.session_id).delete()
        self.db.commit()


class AIAgent:
    def __init__(self, db: Session, session_id: str):
        self.db = db
        self.session_id = session_id
        self.emp_repo = EmployeeRepository(db)
        self.seat_repo = SeatRepository(db)
        self.proj_repo = ProjectRepository(db)

    def run(self, query: str) -> AIResponse:
        # Determine which model is available
        llm = None
        source = "rule_based"

        if settings.GEMINI_API_KEY:
            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.3
            )
            source = "gemini"
        elif settings.GROK_API_KEY or settings.XAI_API_KEY:
            from langchain_openai import ChatOpenAI
            api_key = settings.GROK_API_KEY or settings.XAI_API_KEY
            llm = ChatOpenAI(
                model="grok-beta",
                openai_api_key=api_key,
                openai_api_base="https://api.xai.com/v1",
                temperature=0.3
            )
            source = "grok"
        elif settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.3
            )
            source = "openai"

        # Fallback if no LLM configured
        if not llm:
            return AIResponse(
                answer="No AI credentials (Gemini/Grok/OpenAI) are configured. Please run in rule-based mode or supply API keys.",
                intent="unknown",
                confidence=0.0,
                source="rule_based",
                session_id=self.session_id
            )

        # Define DB querying tools
        @tool
        def get_employee_seat(email_or_name: str) -> str:
            """Useful to get the seat allocation details of a specific employee by name or email."""
            # Search by email first
            emp = None
            if "@" in email_or_name:
                emp = self.emp_repo.get_by_email(email_or_name)
            if not emp:
                employees, _ = self.emp_repo.search(query=email_or_name, limit=1)
                if employees:
                    emp = employees[0]
            
            if not emp:
                return f"No employee found matching '{email_or_name}'."
            
            emp_details = self.emp_repo.get_with_details(emp.id)
            alloc = self.emp_repo.get_active_allocation(emp.id)
            proj_name = emp_details.project.name if emp_details.project else "No Project"
            
            if not alloc or not alloc.seat:
                return f"{emp_details.name} is assigned to Project {proj_name} but has no active seat allocation."
            
            seat = alloc.seat
            return (
                f"{emp_details.name} (Email: {emp_details.email}) sits at Floor {seat.floor}, "
                f"Zone {seat.zone}, Bay {seat.bay}, Seat {seat.seat_number}. Project: {proj_name}."
            )

        @tool
        def search_seats(floor: Optional[int] = None, zone: Optional[str] = None, status: Optional[str] = None) -> str:
            """Useful to list available, occupied, or reserved seats matching criteria like floor or zone."""
            seats, _ = self.seat_repo.search(floor=floor, zone=zone, status=status, limit=15)
            if not seats:
                return "No seats found matching the specified parameters."
            
            output = []
            for s in seats:
                output.append(f"Seat ID: {s.id}, Floor {s.floor}, Zone {s.zone}, {s.bay}, Seat #{s.seat_number} - Status: {s.status}")
            return "\n".join(output)

        @tool
        def get_seat_utilization() -> str:
            """Useful to fetch seat capacity stats and occupancy metrics across the entire office."""
            total = self.seat_repo.count()
            occupied = self.seat_repo.count(status="OCCUPIED")
            available = self.seat_repo.count(status="AVAILABLE")
            reserved = self.seat_repo.count(status="RESERVED")
            maintenance = self.seat_repo.count(status="MAINTENANCE")
            
            rate = (occupied / total * 100) if total > 0 else 0
            return (
                f"Total Seats: {total}, Occupied: {occupied}, Available: {available}, "
                f"Reserved: {reserved}, Maintenance: {maintenance}. "
                f"Current Occupancy Rate is {rate:.1f}%."
            )

        @tool
        def search_projects(query: str) -> str:
            """Useful to find project information and list project managers."""
            projects, _ = self.proj_repo.search(query=query, limit=5)
            if not projects:
                return f"No projects found matching '{query}'."
            
            output = []
            for p in projects:
                output.append(f"Project: {p.name}, Manager: {p.manager_name}, Status: {p.status}")
            return "\n".join(output)

        @tool
        def find_neighbors(email_or_name: str) -> str:
            """Useful to get adjacent co-workers seated near an employee in their same zone."""
            emp = None
            if "@" in email_or_name:
                emp = self.emp_repo.get_by_email(email_or_name)
            if not emp:
                employees, _ = self.emp_repo.search(query=email_or_name, limit=1)
                if employees:
                    emp = employees[0]
            
            if not emp:
                return f"Employee '{email_or_name}' not found."
            
            alloc = self.emp_repo.get_active_allocation(emp.id)
            if not alloc or not alloc.seat:
                return f"{emp.name} is not seated."
            
            seat = alloc.seat
            nearby, _ = self.seat_repo.search(floor=seat.floor, zone=seat.zone, limit=10)
            neighbors = []
            for s in nearby:
                active = self.seat_repo.get_active_allocation_for_seat(s.id)
                if active and active.employee_id != emp.id and active.employee:
                    neighbors.append(active.employee.name)
            
            if neighbors:
                return f"Co-workers seated near {emp.name} on Floor {seat.floor}, Zone {seat.zone}: {', '.join(neighbors[:5])}."
            return f"No active neighbors found near {emp.name} in Zone {seat.zone}."

        tools = [get_employee_seat, search_seats, get_seat_utilization, search_projects, find_neighbors]

        # Setup prompt with history
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are Ethara's AI Assistant for Seat Allocation and Project Mapping.\n"
                "You have access to real-time office floor plans, projects, and employee assignments.\n"
                "Always look up database data using your tools before answering questions about seats, occupancy, neighbors, or assignments.\n"
                "Answer user questions accurately and concisely."
            )),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

        # Wrap in history manager
        agent_with_chat_history = RunnableWithMessageHistory(
            agent_executor,
            lambda sid: DatabaseChatMessageHistory(self.db, sid),
            input_messages_key="input",
            history_messages_key="chat_history",
        )

        try:
            res = agent_with_chat_history.invoke(
                {"input": query},
                config={"configurable": {"session_id": self.session_id}}
            )
            answer = res["output"]
            return AIResponse(
                answer=answer,
                intent="langchain_agent",
                confidence=0.9,
                source=source,
                session_id=self.session_id
            )
        except Exception as e:
            return AIResponse(
                answer=f"An error occurred while executing the AI agent: {str(e)}",
                intent="unknown",
                confidence=0.0,
                source=source,
                session_id=self.session_id
            )
