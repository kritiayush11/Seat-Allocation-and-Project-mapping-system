import pytest
from unittest.mock import patch, MagicMock
from app.schemas.ai_assistant import AIQuery, AIResponse
from app.models.chat_message import ChatMessage


def test_ai_query_accepts_session_id():
    """TDD: Verify AIQuery Pydantic schema accepts optional session_id."""
    query = AIQuery(query="Where is Amit seated?", session_id="test-session-123")
    assert query.query == "Where is Amit seated?"
    assert query.session_id == "test-session-123"


def test_ai_response_includes_session_id():
    """TDD: Verify AIResponse Pydantic schema contains optional session_id."""
    resp = AIResponse(
        answer="Amit is seated on Floor 2.",
        intent="find_seat",
        source="rule_based",
        session_id="test-session-123"
    )
    assert resp.answer == "Amit is seated on Floor 2."
    assert resp.session_id == "test-session-123"


def test_chat_message_db_model_attributes(db_session):
    """TDD: Verify ChatMessage DB model attributes work correctly."""
    msg = ChatMessage(
        session_id="session-xyz",
        role="user",
        content="Hello assistant!"
    )
    db_session.add(msg)
    db_session.commit()

    retrieved = db_session.query(ChatMessage).filter_by(session_id="session-xyz").first()
    assert retrieved is not None
    assert retrieved.role == "user"
    assert retrieved.content == "Hello assistant!"
    
    # Cleanup
    db_session.delete(retrieved)
    db_session.commit()


@patch("app.services.ai_agent.AIAgent.run")
@patch("app.services.ai_assistant_service.settings")
def test_ai_endpoint_with_session_id(mock_settings, mock_agent_run, client):
    """TDD: Verify endpoint uses agent memory when session_id is provided."""
    mock_settings.GEMINI_API_KEY = "mock-key"
    mock_agent_run.return_value = AIResponse(
        answer="I remember you. You are Test User.",
        intent="conversational",
        source="openai",
        session_id="session-abc"
    )

    r = client.post(
        "/ai/query",
        json={"query": "Who am I?", "session_id": "session-abc"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["answer"] == "I remember you. You are Test User."
    assert data["session_id"] == "session-abc"
    mock_agent_run.assert_called_once()
