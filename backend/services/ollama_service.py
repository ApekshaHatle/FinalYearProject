"""Ollama service — faster responses with semantic cache"""
import httpx
import json
import hashlib
import time
from typing import Optional, List, Dict, AsyncGenerator
from backend.core.config import OLLAMA_BASE_URL, OLLAMA_MODEL

# ── Simple in-process semantic cache ─────────────────────────────────────────
# Key: SHA256(model + prompt[:200])  →  (answer, timestamp)
# Shared across ALL requests in this process (reset on restart).
# For cross-restart persistence you'd store in Redis/Supabase,
# but this already gives a huge speedup for repeated/similar questions
# during a session or across sessions in the same run.

_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 3600   # 1 hour — tune as needed


def _cache_key(model: str, prompt: str) -> str:
    raw = f"{model}||{prompt[:300]}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _cache_get(key: str) -> Optional[str]:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[1]) < _CACHE_TTL_SECONDS:
        return entry[0]
    return None


def _cache_set(key: str, value: str) -> None:
    _CACHE[key] = (value, time.time())


# ── Service ───────────────────────────────────────────────────────────────────

class OllamaService:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.is_connected = False

    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"{self.base_url}/api/tags", timeout=5.0)
                if r.status_code == 200:
                    self.is_connected = True
                    models = r.json().get("models", [])
                    print(f"✅ Ollama connected. Models: {[m['name'] for m in models]}")
                    return True
        except Exception as e:
            print(f"❌ Ollama not connected: {e}\n💡 Run: ollama serve")
            self.is_connected = False
        return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 600,          # ← was 2000; shorter = faster
        use_cache: bool = True,
    ) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                # Speed-up flags — safe for all Ollama models
                "num_ctx": 2048,        # ← smaller context window = faster
                "repeat_penalty": 1.1,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        # Cache check
        if use_cache:
            key = _cache_key(self.model, (system_prompt or "") + prompt)
            cached = _cache_get(key)
            if cached:
                print("⚡ Cache hit")
                return cached

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:   # was 180s
                r = await client.post(f"{self.base_url}/api/generate", json=payload)
                r.raise_for_status()
                answer = r.json()["response"]
                if use_cache:
                    _cache_set(key, answer)
                return answer
        except Exception as e:
            raise Exception(f"Ollama generation failed: {str(e)}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": 400,     # ← shorter stream too
                "num_ctx": 2048,
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as r:
                    async for line in r.aiter_lines():
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
        chat_history: Optional[List[Dict]] = None,
        use_cache: bool = True,
    ) -> str:
        """
        RAG response — concise by default.
        The key change vs before: much shorter system prompt + 600 token cap.
        This cuts latency significantly while keeping answer quality.
        """
        # Limit context to top 3 chunks to reduce prompt size
        top_context = context[:3]
        context_text = "\n\n".join(
            f"[Doc {i+1}]: {doc[:600]}"   # cap each chunk to 600 chars
            for i, doc in enumerate(top_context)
        )

        # Last 3 turns of history (not 5)
        history = ""
        if chat_history:
            recent = chat_history[-3:]
            history = "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in recent)

        # ── Shorter, direct system prompt ─────────────────────────────────────
        system_prompt = (
            "You are a concise coding assistant. "
            "Answer using the provided docs. "
            "Be direct and brief. Code examples only when essential. "
            "If the answer isn't in the docs, say so in one sentence."
        )

        prompt = f"""Docs:
{context_text}
{f"History:{chr(10)}{history}" if history else ""}
Q: {question}
A:"""

        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.2,            # lower = more deterministic = faster
            max_tokens=600,
            use_cache=use_cache,
        )

    async def generate_code(self, description: str, language: str = "python") -> str:
        system_prompt = (
            f"Expert {language} programmer. "
            "Return only the code, no explanation unless asked."
        )
        prompt = f"Write {language} code for: {description}\n\nCode:"
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.15,
            max_tokens=800,
        )

    def cache_stats(self) -> dict:
        """Quick stats for debugging."""
        now = time.time()
        live = sum(1 for _, (_, ts) in _CACHE.items() if now - ts < _CACHE_TTL_SECONDS)
        return {"total_entries": len(_CACHE), "live_entries": live, "ttl_seconds": _CACHE_TTL_SECONDS}


ollama_service = OllamaService()