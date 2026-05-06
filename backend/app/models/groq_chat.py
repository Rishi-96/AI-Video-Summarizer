import logging
import os
import httpx
from typing import AsyncGenerator, Dict, List, Optional
from groq import Groq

from app.core.constants import (
    GROQ_CHAT_MODEL,
    OLLAMA_MODEL,
    OLLAMA_GENERATE_URL,
    OLLAMA_TAGS_URL,
    MAX_CHAT_TRANSCRIPT_CHARS,
)

logger = logging.getLogger(__name__)

class GroqChat:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client: Optional[Groq] = None
        self.history: List[Dict] = []
        self.use_mock = False
        self.use_ollama = False
        self.ollama_url = OLLAMA_GENERATE_URL

        try:
            http_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
            _disable_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
            http_client = httpx.Client(
                proxy=http_proxy,
                verify=not _disable_ssl,
            )
            
            # Check for Ollama
            try:
                ollama_check = httpx.get(OLLAMA_TAGS_URL, timeout=1.0)
                if ollama_check.status_code == 200:
                    self.use_ollama = True
                    logger.info("Chat: Ollama detected")
            except Exception:
                pass

            if not self.use_ollama:
                if api_key:
                    self.client = Groq(api_key=api_key, http_client=http_client)
                    logger.info("Groq client initialized")
                else:
                    logger.warning("No GROQ_API_KEY set and Ollama not detected — running in mock mode")
                    self.use_mock = True
        except Exception as e:
            logger.warning("Error initializing AI backend: %s", e)
            self.use_mock = True

    def set_context(
        self,
        transcript: str,
        summary: str,
        video_info: Dict,
        key_points: List[str],
    ) -> None:
        """Prime the conversation with video context."""
        system_prompt = (
            "You are an AI assistant that helps users understand video content.\n\n"
            f"VIDEO TITLE: {video_info.get('original_name', 'Unknown')}\n"
            f"DURATION: {video_info.get('duration', 0)} seconds\n\n"
            f"TRANSCRIPT (first {MAX_CHAT_TRANSCRIPT_CHARS} chars):\n{transcript[:MAX_CHAT_TRANSCRIPT_CHARS]}\n\n"
            f"SUMMARY:\n{summary}\n\n"
            f"KEY POINTS:\n{', '.join(key_points[:10])}\n\n"
            "Instructions:\n"
            "1. Answer ONLY based on the video content above.\n"
            "2. Politely decline off-topic questions.\n"
            "3. Be helpful, accurate, and conversational."
        )
        self.history = [{"role": "system", "content": system_prompt}]

    async def ask_question(self, question: str) -> str:
        """Send a question and return the full response string."""
        if self.use_ollama:
            # Construct a simple prompt from history
            prompt = "\n".join([f"{m['role']}: {m['content']}" for m in self.history])
            prompt += f"\nuser: {question}\nassistant:"
            
            try:
                resp = httpx.post(self.ollama_url, json={
                "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }, timeout=60.0)
                answer = resp.json().get("response", "").strip()
                self.history.append({"role": "user", "content": question})
                self.history.append({"role": "assistant", "content": answer})
                return answer
            except Exception as e:
                logger.error("Ollama chat error: %s", e)
                return f"Error connecting to Ollama: {e}"

        if self.use_mock or self.client is None:
            return self._mock_response(question)

        self.history.append({"role": "user", "content": question})
        try:
            resp = self.client.chat.completions.create(
                messages=self.history,
                model=GROQ_CHAT_MODEL,
            )
            answer = resp.choices[0].message.content
            self.history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            self.history.pop()  # remove unanswered user turn
            logger.warning("Groq chat error: %s", e)
            return f"I'm having trouble answering right now. Please try again. ({e})"

    async def stream_question(self, question: str) -> AsyncGenerator[str, None]:
        """Yield response tokens one-by-one for WebSocket streaming."""
        if self.use_ollama:
            answer = await self.ask_question(question)
            yield answer
            return

        if self.use_mock or self.client is None:
            yield self._mock_response(question)
            return

        self.history.append({"role": "user", "content": question})
        full_answer = ""
        try:
            stream = self.client.chat.completions.create(
                messages=self.history,
                model=GROQ_CHAT_MODEL,
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    full_answer += token
                    yield token

            self.history.append({"role": "assistant", "content": full_answer})
        except Exception as e:
            self.history.pop()
            logger.warning("Groq streaming error: %s", e)
            yield f"[Error: {e}]"

    def _mock_response(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ("summary", "about", "what is")):
            return "Based on the video, it appears to cover AI technology and video processing techniques."
        if any(w in q for w in ("duration", "how long")):
            return "The video duration is shown in the player controls."
        if any(w in q for w in ("key point", "main idea")):
            return "Main points include: 1) AI video processing, 2) Transcription, 3) Summarization methods."
        if "language" in q:
            return "The video appears to be in English."
        if "thank" in q:
            return "You're welcome! Feel free to ask anything else about the video."
        return "Could you rephrase that? I'll do my best to answer using the video content."
