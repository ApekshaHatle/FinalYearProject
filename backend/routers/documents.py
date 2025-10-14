"""Document management endpoints"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import os
import shutil
from backend.db.database import get_db
from backend.core.models import Document
from backend.services.rag_service import rag_service
from backend.core.config import UPLOAD_DIR, MAX_UPLOAD_SIZE_MB

router = APIRouter()

# Schemas
class DocumentResponse(BaseModel):
    id: str
    title: str
    filename: str
    chunk_count: int
    status: str
    uploaded_at: str
    
    class Config:
        from_attributes = True

# Background task to process document
async def process_document_task(document_id: str, file_path: str, db: Session):
    """Background task to process uploaded document"""
    try:
        # Add to vector store
        chunk_count = await rag_service.add_document(
            file_path=file_path,
            document_id=document_id,
            metadata={"filename": os.path.basename(file_path)}
        )
        
        # Update document status
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.chunk_count = chunk_count
            doc.status = "completed"
            db.commit()
        
        print(f"✅ Processed document {document_id}")
        
    except Exception as e:
        print(f"❌ Error processing document {document_id}: {e}")
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = "failed"
            db.commit()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload and process document"""
    
    # Validate file type
    allowed_extensions = ['.pdf', '.txt', '.md', '.docx']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create upload directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    file_size = os.path.getsize(file_path)
    
    # Check size
    if file_size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {MAX_UPLOAD_SIZE_MB}MB"
        )
    
    # Create document record
    document = Document(
        title=file.filename,
        filename=file.filename,
        file_path=file_path,
        status="processing"
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process in background
    background_tasks.add_task(process_document_task, document.id, file_path, db)
    
    return document

@router.get("/", response_model=List[DocumentResponse])
def list_documents(db: Session = Depends(get_db)):
    """Get all documents"""
    documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
    
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "chunk_count": doc.chunk_count,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at.isoformat()
        }
        for doc in documents
    ]

@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: str, db: Session = Depends(get_db)):
    """Get document by ID"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return doc

@router.delete("/{document_id}")
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """Delete document"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete from vector store
    await rag_service.delete_document(document_id)
    
    # Delete file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    
    # Delete from database
    db.delete(doc)
    db.commit()
    
    return {"message": "Document deleted successfully"}

@router.get("/{document_id}/status")
def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """Get document processing status"""
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "id": doc.id,
        "status": doc.status,
        "chunk_count": doc.chunk_count
    }