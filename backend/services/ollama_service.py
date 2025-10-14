"""Ollama service for Code Llama integration"""
import httpx
import json
from typing import Optional, List, Dict, AsyncGenerator
from backend.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaService:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.is_connected = False
    
    async def check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if response.status_code == 200:
                    self.is_connected = True
                    models = response.json().get("models", [])
                    print(f"✅ Ollama connected. Models: {[m['name'] for m in models]}")
                    return True
        except Exception as e:
            print(f"❌ Ollama not connected: {e}")
            print("💡 Run: ollama serve")
            self.is_connected = False
        return False
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text with Code Llama"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                return response.json()["response"]
        except Exception as e:
            raise Exception(f"Ollama generation failed: {str(e)}")
    
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream generation token by token"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature,
                        "num_predict": min(max_tokens, 500) }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if line.strip():
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"Error: {str(e)}"
    
    async def generate_with_context(
        self,
        question: str,
        context: List[str],
        chat_history: Optional[List[Dict]] = None
    ) -> str:
        """Generate RAG response with document context"""
        
        # Build context
        context_text = "\n\n".join([
            f"Document {i+1}:\n{doc}"
            for i, doc in enumerate(context)
        ])
        
        # Build history
        history = ""
        if chat_history:
            history = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in chat_history[-5:]
            ])
        
        system_prompt = """You are an expert code assistant with access to company documentation.

Guidelines:
- Answer accurately using the provided context
- Cite which document you're referencing
- Provide working code examples when relevant
- If information isn't in the documents, say so clearly
- Follow coding best practices"""
        
        prompt = f"""Company Documentation:
{context_text}

{"Previous Conversation:" if history else ""}
{history}

Question: {question}

Answer:"""
        
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
    
    async def generate_code(
        self,
        description: str,
        language: str = "python"
    ) -> str:
        """Generate code snippet"""
        system_prompt = f"""You are an expert {language} programmer.
Generate clean, production-ready code with comments and error handling."""
        
        prompt = f"""Generate {language} code for:

{description}

Code:"""
        
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2
        )

# Singleton instance
ollama_service = OllamaService()