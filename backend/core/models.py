from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.db.database import Base
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    documents = relationship("Document", back_populates="owner")
    chat_sessions = relationship("ChatSession", back_populates="user")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"))
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="pending")
    uploaded_at = Column(DateTime, server_default=func.now())
    
    owner = relationship("User", back_populates="documents")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("Message", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    sources = Column(JSON, default=list)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())
    
    session = relationship("ChatSession", back_populates="messages")