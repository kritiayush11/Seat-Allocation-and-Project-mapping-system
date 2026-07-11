"""
ChatMessage ORM model for storing conversation history.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from ..database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ChatMessage id={self.id} session_id={self.session_id} role={self.role}>"
