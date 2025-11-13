"""RAG Debug and Verification Endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from backend.db.database import get_db
from backend.services.rag_service import rag_service
from backend.routers.auth import get_current_admin_user
from backend.core.models import User

router = APIRouter()

class VectorSearchRequest(BaseModel):
    query: str
    k: int = 5

class VectorStats(BaseModel):
    total_chunks: int
    total_documents: int
    embedding_dimension: int
    sample_chunks: List[Dict]

@router.get("/vector-stats")
async def get_vector_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """Get detailed vector database statistics - ADMIN ONLY"""
    
    if not rag_service.is_initialized:
        return {"error": "RAG service not initialized"}
    
    try:
        # Get ChromaDB collection
        collection = rag_service.vectorstore._collection
        
        # Get total count
        total_chunks = collection.count()
        
        # Get sample data (first 5 chunks)
        results = collection.get(
            limit=5,
            include=['embeddings', 'documents', 'metadatas']
        )
        
        # Count unique documents
        unique_docs = set()
        if results['metadatas']:
            for metadata in results['metadatas']:
                if 'document_id' in metadata:
                    unique_docs.add(metadata['document_id'])
        
        # Get embedding dimension
        embedding_dim = 0
        if results['embeddings'] and len(results['embeddings']) > 0:
            embedding_dim = len(results['embeddings'][0])
        
        # Format sample chunks
        sample_chunks = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][:5]):
                chunk_data = {
                    'id': results['ids'][i] if results['ids'] else None,
                    'content_preview': doc[:200] + '...' if len(doc) > 200 else doc,
                    'metadata': results['metadatas'][i] if results['metadatas'] else {},
                    'embedding_sample': results['embeddings'][i][:10] if results['embeddings'] else []
                }
                sample_chunks.append(chunk_data)
        
        return {
            "status": "initialized",
            "total_chunks": total_chunks,
            "unique_documents": len(unique_docs),
            "embedding_dimension": embedding_dim,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "persist_directory": rag_service.persist_directory,
            "sample_chunks": sample_chunks
        }
        
    except Exception as e:
        return {"error": str(e)}

@router.post("/test-search")
async def test_vector_search(
    request: VectorSearchRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """Test vector search with detailed results - ADMIN ONLY"""
    
    if not rag_service.is_initialized:
        raise HTTPException(status_code=500, detail="RAG service not initialized")
    
    try:
        # Perform search
        results = await rag_service.search(
            query=request.query,
            k=request.k
        )
        
        # Get similarity scores
        scored_results = await rag_service.search_with_scores(
            query=request.query,
            k=request.k
        )
        
        # Format results with scores
        formatted_results = []
        for i, result in enumerate(results):
            score = scored_results[i][1] if i < len(scored_results) else 0
            formatted_results.append({
                'rank': i + 1,
                'content': result['content'],
                'similarity_score': round(score, 4),
                'metadata': result['metadata'],
                'source': result['source']
            })
        
        return {
            "query": request.query,
            "total_results": len(formatted_results),
            "results": formatted_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/document-chunks/{document_id}")
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get all chunks for a specific document - ADMIN ONLY"""
    
    if not rag_service.is_initialized:
        raise HTTPException(status_code=500, detail="RAG service not initialized")
    
    try:
        collection = rag_service.vectorstore._collection
        
        # Get all chunks for this document
        results = collection.get(
            where={"document_id": document_id},
            include=['documents', 'metadatas', 'embeddings']
        )
        
        chunks = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                chunks.append({
                    'chunk_index': results['metadatas'][i].get('chunk_index', i),
                    'content': doc,
                    'content_length': len(doc),
                    'has_embedding': results['embeddings'][i] is not None if results['embeddings'] else False,
                    'embedding_preview': results['embeddings'][i][:5] if results['embeddings'] and results['embeddings'][i] else []
                })
        
        return {
            "document_id": document_id,
            "total_chunks": len(chunks),
            "chunks": sorted(chunks, key=lambda x: x['chunk_index'])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare-queries")
async def compare_rag_vs_raw(
    query: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Compare RAG response vs raw LLM response"""
    from backend.services.ollama_service import ollama_service
    
    # Get RAG response (with context)
    search_results = await rag_service.search(query=query, k=3)
    context_docs = [result["content"] for result in search_results]
    
    rag_response = await ollama_service.generate_with_context(
        question=query,
        context=context_docs,
        chat_history=[]
    )
    
    # Get raw LLM response (no context)
    raw_response = await ollama_service.generate(
        prompt=query,
        system_prompt="You are a helpful coding assistant.",
        temperature=0.7
    )
    
    return {
        "query": query,
        "rag_response": {
            "answer": rag_response,
            "sources_used": len(context_docs),
            "source_previews": [doc[:100] + "..." for doc in context_docs]
        },
        "raw_llm_response": {
            "answer": raw_response,
            "sources_used": 0
        },
        "comparison": {
            "rag_length": len(rag_response),
            "raw_length": len(raw_response),
            "uses_company_docs": len(context_docs) > 0
        }
    }

@router.get("/embedding-visualization/{document_id}")
async def visualize_embeddings(
    document_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Get embedding data for visualization - ADMIN ONLY"""
    
    if not rag_service.is_initialized:
        raise HTTPException(status_code=500, detail="RAG service not initialized")
    
    try:
        collection = rag_service.vectorstore._collection
        
        results = collection.get(
            where={"document_id": document_id},
            include=['embeddings', 'documents', 'metadatas']
        )
        
        if not results['embeddings']:
            return {"error": "No embeddings found"}
        
        # Return first 3 embeddings with their text
        visualization_data = []
        for i in range(min(3, len(results['embeddings']))):
            visualization_data.append({
                'chunk_index': i,
                'text_preview': results['documents'][i][:100] + "...",
                'embedding_vector': results['embeddings'][i],
                'embedding_dimension': len(results['embeddings'][i]),
                'embedding_preview': {
                    'first_10_values': results['embeddings'][i][:10],
                    'min_value': min(results['embeddings'][i]),
                    'max_value': max(results['embeddings'][i]),
                    'mean_value': sum(results['embeddings'][i]) / len(results['embeddings'][i])
                }
            })
        
        return {
            "document_id": document_id,
            "total_chunks": len(results['embeddings']),
            "embedding_dimension": len(results['embeddings'][0]),
            "sample_embeddings": visualization_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))