from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from backend.db.database import engine, Base
from backend.routers import auth, chat, documents, admin
from backend.services.ollama_service import ollama_service
from backend.services.rag_service import rag_service
import os
import uvicorn

# ---------- DATABASE SETUP ----------
Base.metadata.create_all(bind=engine)

# ---------- DIRECTORIES ----------
os.makedirs("uploads", exist_ok=True)
os.makedirs("vectordb", exist_ok=True)

# ---------- APP INITIALIZATION ----------
app = FastAPI(
    title="Enterprise Code Assistant",
    description="AI Code Assistant with RAG",
    version="1.0.0"
)

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js default port
        "http://localhost:5173"   # Vite/React default port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Pydantic MODELS ----------
class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    session_id: str

class DocumentUpload(BaseModel):
    filename: str
    content: str

class HealthResponse(BaseModel):
    status: str
    message: str

# ---------- ROUTERS ----------
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# ---------- STARTUP EVENTS ----------
@app.on_event("startup")
async def startup():
    print("🚀 Starting Code Assistant...")
    await ollama_service.check_connection()
    await rag_service.initialize()
    print("✅ Ready!")

# ---------- ROOT & HEALTH ----------
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Enterprise Code Assistant API is running"}

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy" if rag_service.is_initialized and ollama_service.is_connected else "starting",
        "message": "All systems operational" if rag_service.is_initialized else "Initializing RAG or Ollama"
    }

# ---------- MOCK API ENDPOINTS (for testing / placeholder) ----------
@app.post("/api/mock/chat", response_model=ChatResponse)
async def chat_mock(request: ChatRequest):
    """Temporary chat endpoint (mock)"""
    mock_response = f"You asked: {request.query}. RAG integration coming soon!"
    return {
        "answer": mock_response,
        "sources": ["doc1.pdf", "doc2.md"],
        "session_id": request.session_id or "session_123"
    }

@app.post("/api/mock/documents/upload")
async def upload_document_mock(doc: DocumentUpload):
    """Temporary document upload mock"""
    return {
        "status": "success",
        "message": f"Document {doc.filename} uploaded successfully",
        "document_id": "doc_123"
    }

@app.get("/api/mock/documents")
async def list_documents_mock():
    """Temporary document listing mock"""
    return {
        "documents": [
            {"id": "1", "name": "API_Guide.pdf", "uploaded_at": "2024-01-01"},
            {"id": "2", "name": "Security_Policy.md", "uploaded_at": "2024-01-02"}
        ]
    }

@app.delete("/api/mock/documents/{doc_id}")
async def delete_document_mock(doc_id: str):
    """Temporary document delete mock"""
    return {
        "status": "success",
        "message": f"Document {doc_id} deleted"
    }

# ---------- MAIN ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
