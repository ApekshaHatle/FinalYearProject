"""RAG Evaluation System"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict
from backend.db.database import get_db
from backend.services.rag_service import rag_service
from backend.services.ollama_service import ollama_service
from backend.routers.auth import get_current_admin_user
from backend.core.models import User, QueryMetrics
import time

router = APIRouter()

class EvaluationQuestion(BaseModel):
    question: str
    expected_keywords: List[str]
    ground_truth: str = None

class EvaluationResult(BaseModel):
    question: str
    answer: str
    sources_found: int
    response_time_ms: int
    keyword_match_score: float
    contains_expected_keywords: List[str]
    missing_keywords: List[str]

@router.post("/evaluate-rag")
async def evaluate_rag_system(
    questions: List[EvaluationQuestion],
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Evaluate RAG system performance
    
    Metrics:
    1. Retrieval Success Rate
    2. Response Time
    3. Keyword Coverage
    4. Source Quality
    """
    
    results = []
    total_time = 0
    successful_retrievals = 0
    
    for question in questions:
        start_time = time.time()
        
        # Perform RAG query
        search_results = await rag_service.search(query=question.question, k=5)
        context_docs = [result["content"] for result in search_results]
        
        if context_docs:
            successful_retrievals += 1
        
        # Generate answer
        answer = await ollama_service.generate_with_context(
            question=question.question,
            context=context_docs,
            chat_history=[]
        )
        
        response_time = int((time.time() - start_time) * 1000)
        total_time += response_time
        
        # Calculate keyword match score
        answer_lower = answer.lower()
        matched_keywords = [kw for kw in question.expected_keywords if kw.lower() in answer_lower]
        missing_keywords = [kw for kw in question.expected_keywords if kw.lower() not in answer_lower]
        
        keyword_score = len(matched_keywords) / len(question.expected_keywords) if question.expected_keywords else 0
        
        results.append({
            "question": question.question,
            "answer": answer,
            "sources_found": len(context_docs),
            "response_time_ms": response_time,
            "keyword_match_score": round(keyword_score, 2),
            "contains_expected_keywords": matched_keywords,
            "missing_keywords": missing_keywords
        })
    
    # Calculate overall metrics
    avg_response_time = total_time / len(questions) if questions else 0
    retrieval_success_rate = (successful_retrievals / len(questions)) * 100 if questions else 0
    avg_keyword_score = sum(r['keyword_match_score'] for r in results) / len(results) if results else 0
    
    return {
        "summary": {
            "total_questions": len(questions),
            "avg_response_time_ms": round(avg_response_time, 2),
            "retrieval_success_rate": round(retrieval_success_rate, 2),
            "avg_keyword_coverage": round(avg_keyword_score * 100, 2),
            "total_evaluation_time_s": round(total_time / 1000, 2)
        },
        "detailed_results": results
    }

@router.get("/performance-metrics")
async def get_performance_metrics(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get overall system performance metrics"""
    
    # Get all query metrics from database
    metrics = db.query(QueryMetrics).all()
    
    if not metrics:
        return {"error": "No metrics data available"}
    
    # Calculate statistics
    response_times = [m.response_time_ms for m in metrics if m.response_time_ms]
    num_sources = [m.num_sources for m in metrics]
    success_count = sum(1 for m in metrics if m.success)
    
    return {
        "total_queries": len(metrics),
        "success_rate": round((success_count / len(metrics)) * 100, 2),
        "response_time": {
            "min_ms": min(response_times) if response_times else 0,
            "max_ms": max(response_times) if response_times else 0,
            "avg_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
            "median_ms": sorted(response_times)[len(response_times)//2] if response_times else 0
        },
        "sources_per_query": {
            "min": min(num_sources) if num_sources else 0,
            "max": max(num_sources) if num_sources else 0,
            "avg": round(sum(num_sources) / len(num_sources), 2) if num_sources else 0
        },
        "rag_effectiveness": {
            "queries_with_sources": sum(1 for n in num_sources if n > 0),
            "queries_without_sources": sum(1 for n in num_sources if n == 0),
            "avg_sources_when_found": round(
                sum(n for n in num_sources if n > 0) / sum(1 for n in num_sources if n > 0), 2
            ) if sum(1 for n in num_sources if n > 0) > 0 else 0
        }
    }

@router.post("/test-retrieval-quality")
async def test_retrieval_quality(
    test_queries: List[str],
    current_user: User = Depends(get_current_admin_user)
):
    """
    Test retrieval quality with various query types
    
    Metrics:
    - Retrieval@K (how many relevant docs in top K)
    - Average similarity score
    - Consistency across similar queries
    """
    
    results = []
    
    for query in test_queries:
        # Get search results with scores
        scored_results = await rag_service.search_with_scores(query=query, k=5)
        
        if scored_results:
            scores = [score for _, score in scored_results]
            avg_score = sum(scores) / len(scores)
            
            results.append({
                "query": query,
                "documents_found": len(scored_results),
                "avg_similarity_score": round(avg_score, 4),
                "top_score": round(scores[0], 4) if scores else 0,
                "score_distribution": {
                    "excellent (>0.8)": sum(1 for s in scores if s > 0.8),
                    "good (0.6-0.8)": sum(1 for s in scores if 0.6 <= s <= 0.8),
                    "fair (0.4-0.6)": sum(1 for s in scores if 0.4 <= s < 0.6),
                    "poor (<0.4)": sum(1 for s in scores if s < 0.4)
                }
            })
        else:
            results.append({
                "query": query,
                "documents_found": 0,
                "avg_similarity_score": 0,
                "error": "No documents retrieved"
            })
    
    # Calculate overall quality
    total_docs_found = sum(r['documents_found'] for r in results)
    queries_with_results = sum(1 for r in results if r['documents_found'] > 0)
    avg_similarity = sum(r.get('avg_similarity_score', 0) for r in results) / len(results)
    
    return {
        "test_summary": {
            "total_queries": len(test_queries),
            "queries_with_results": queries_with_results,
            "retrieval_success_rate": round((queries_with_results / len(test_queries)) * 100, 2),
            "avg_documents_per_query": round(total_docs_found / len(test_queries), 2),
            "avg_similarity_score": round(avg_similarity, 4)
        },
        "detailed_results": results,
        "recommendation": "Excellent" if avg_similarity > 0.7 else "Good" if avg_similarity > 0.5 else "Needs Improvement"
    }

@router.get("/comparison-baseline")
async def compare_with_baseline(
    sample_questions: List[str] = [
        "How do I authenticate?",
        "What is the database schema?",
        "Explain the API endpoints"
    ],
    current_user: User = Depends(get_current_admin_user)
):
    """Compare RAG vs non-RAG performance"""
    
    comparisons = []
    
    for question in sample_questions:
        # RAG response
        rag_start = time.time()
        search_results = await rag_service.search(query=question, k=3)
        context_docs = [result["content"] for result in search_results]
        rag_answer = await ollama_service.generate_with_context(
            question=question,
            context=context_docs,
            chat_history=[]
        )
        rag_time = int((time.time() - rag_start) * 1000)
        
        # Non-RAG response
        norag_start = time.time()
        norag_answer = await ollama_service.generate(
            prompt=question,
            system_prompt="You are a helpful coding assistant.",
            temperature=0.7
        )
        norag_time = int((time.time() - norag_start) * 1000)
        
        comparisons.append({
            "question": question,
            "rag": {
                "answer": rag_answer,
                "response_time_ms": rag_time,
                "sources_used": len(context_docs),
                "answer_length": len(rag_answer)
            },
            "no_rag": {
                "answer": norag_answer,
                "response_time_ms": norag_time,
                "sources_used": 0,
                "answer_length": len(norag_answer)
            },
            "improvement": {
                "has_citations": len(context_docs) > 0,
                "more_detailed": len(rag_answer) > len(norag_answer),
                "company_specific": "company" in rag_answer.lower() or "our" in rag_answer.lower()
            }
        })
    
    return {
        "comparison_results": comparisons,
        "summary": {
            "total_tests": len(comparisons),
            "rag_avg_time_ms": round(sum(c['rag']['response_time_ms'] for c in comparisons) / len(comparisons), 2),
            "norag_avg_time_ms": round(sum(c['no_rag']['response_time_ms'] for c in comparisons) / len(comparisons), 2),
            "rag_advantages": sum(1 for c in comparisons if c['improvement']['has_citations'])
        }
    }