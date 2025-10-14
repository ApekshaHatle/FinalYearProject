from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.db.database import engine, Base
from backend.routers import auth, chat, documents, admin
from backend.services.ollama_service import ollama_service
from backend.services.rag_service import rag_service
import os

# Create tables
Base.metadata.create_all(bind=engine)

# Create directories
os.makedirs("uploads", exist_ok=True)
os.makedirs("vectordb", exist_ok=True)

app = FastAPI(
    title="Enterprise Code Assistant",
    description="AI Code Assistant with RAG",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

@app.on_event("startup")
async def startup():
    print("🚀 Starting Code Assistant...")
    await ollama_service.check_connection()
    await rag_service.initialize()
    print("✅ Ready!")

@app.get("/")
def root():
    return {
        "message": "Enterprise Code Assistant API",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ollama": ollama_service.is_connected,
        "rag": rag_service.is_initialized
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)