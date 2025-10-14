"""RAG service for document retrieval"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma
from langchain.document_loaders import PyPDFLoader, TextLoader
from typing import List, Dict, Optional
import os
from backend.core.config import CHROMA_PERSIST_DIR

class RAGService:
    def __init__(self):
        self.persist_directory = CHROMA_PERSIST_DIR
        self.embeddings = None
        self.vectorstore = None
        self.is_initialized = False
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def initialize(self):
        """Initialize embeddings and vector store"""
        try:
            print("📦 Loading embedding model...")
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
            
            if os.path.exists(self.persist_directory):
                print("📂 Loading existing vector database...")
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            else:
                print("🆕 Creating new vector database...")
                os.makedirs(self.persist_directory, exist_ok=True)
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
            
            self.is_initialized = True
            print("✅ RAG service initialized!")
            
        except Exception as e:
            print(f"❌ RAG initialization failed: {e}")
            self.is_initialized = False
            raise
    
    async def add_document(
        self,
        file_path: str,
        document_id: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """Add document to vector store"""
        if not self.is_initialized:
            raise Exception("RAG service not initialized")
        
        try:
            # Load document
            if file_path.endswith('.pdf'):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(('.txt', '.md')):
                loader = TextLoader(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_path}")
            
            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)
            
            # Add metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "document_id": document_id,
                    "chunk_index": i,
                    "source": file_path,
                    **(metadata or {})
                })
            
            # Add to vector store
            self.vectorstore.add_documents(chunks)
            self.vectorstore.persist()
            
            print(f"✅ Added {len(chunks)} chunks from {file_path}")
            return len(chunks)
            
        except Exception as e:
            print(f"❌ Failed to add document: {e}")
            raise
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for relevant documents"""
        if not self.is_initialized:
            raise Exception("RAG service not initialized")
        
        try:
            if filter_metadata:
                results = self.vectorstore.similarity_search(
                    query,
                    k=k,
                    filter=filter_metadata
                )
            else:
                results = self.vectorstore.similarity_search(query, k=k)
            
            formatted_results = []
            for doc in results:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "source": doc.metadata.get("source", "unknown")
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document chunks"""
        if not self.is_initialized:
            raise Exception("RAG service not initialized")
        
        try:
            results = self.vectorstore.get(
                where={"document_id": document_id}
            )
            
            if results and "ids" in results:
                self.vectorstore.delete(ids=results["ids"])
                self.vectorstore.persist()
                print(f"✅ Deleted document {document_id}")
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to delete: {e}")
            return False
    
    async def get_statistics(self) -> Dict:
        """Get vector store stats"""
        if not self.is_initialized:
            return {"error": "Not initialized"}
        
        try:
            collection = self.vectorstore._collection
            return {
                "total_chunks": collection.count(),
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            return {"error": str(e)}

# Singleton instance
rag_service = RAGService()