"""
AI Assistant router.
Rate limits:
  POST /ai/query → 10/minute  (LLM API cost protection)
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..limiter import limiter
from ..services.ai_assistant_service import AIAssistantService
from ..schemas.ai_assistant import AIQuery, AIResponse
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/ai",
    tags=["AI Assistant"],
    dependencies=[Depends(get_current_user)]
)


@router.post(
    "/query",
    response_model=AIResponse,
    summary="Natural language query interface for seat and project information",
)
@limiter.limit("10/minute")
def ai_query(
    request: Request,
    body: AIQuery,
    db: Session = Depends(get_db),
):
    """
    Ask natural language questions about seats, employees, and projects.

    **Examples:**
    - `"Where is Amit seated?"`
    - `"Which project is sara@ethara.ai assigned to?"`
    - `"Show available seats on Floor 3"`
    - `"How many seats are occupied for Project Indigo?"`
    - `"Who is sitting near me? My email is john@ethara.ai"`
    - `"Allocate a seat for a new employee joining today"`

    The system uses a rule-based intent parser first. If `OPENAI_API_KEY` is set,
    complex queries fall back to GPT-4o.
    """
    service = AIAssistantService(db)
    return service.answer(body.query, body.session_id)
