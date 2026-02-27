import logging
from typing import AsyncGenerator, Dict, List, Optional

from groq import Groq

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3-8b-8192"


class GroqChat:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client: Optional[Groq] = None
        self.history: List[Dict] = []
        self.use_mock = False

        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                logger.info("Groq client initialized")
            except Exception as e:
                logger.warning("Error initializing Groq client: %s", e)
                self.use_mock = True
        else:
            logger.warning("No GROQ_API_KEY set — running in mock mode")
            self.use_mock = True

    # ------------------------------------------------------------------
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
            f"TRANSCRIPT (first 2000 chars):\n{transcript[:2000]}\n\n"
            f"SUMMARY:\n{summary}\n\n"
            f"KEY POINTS:\n{', '.join(key_points[:10])}\n\n"
            "Instructions:\n"
            "1. Answer ONLY based on the video content above.\n"
            "2. Politely decline off-topic questions.\n"
            "3. Be helpful, accurate, and conversational."
        )
        self.history = [{"role": "system", "content": system_prompt}]

    # ------------------------------------------------------------------
    async def ask_question(self, question: str) -> str:
        """Send a question and return the full response string."""
        if self.use_mock or self.client is None:
            return self._mock_response(question)

        self.history.append({"role": "user", "content": question})
        try:
            resp = self.client.chat.completions.create(
                messages=self.history,
                model=DEFAULT_MODEL,
            )
            answer = resp.choices[0].message.content
            self.history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as e:
            self.history.pop()  # remove unanswered user turn
            logger.warning("Groq chat error: %s", e)
            return f"I'm having trouble answering right now. Please try again. ({e})"

    # ------------------------------------------------------------------
    async def stream_question(self, question: str) -> AsyncGenerator[str, None]:
        """
        Yield response tokens one-by-one for WebSocket streaming.
        Falls back to a single-chunk yield in mock mode.
        """
        if self.use_mock or self.client is None:
            yield self._mock_response(question)
            return

        self.history.append({"role": "user", "content": question})
        full_answer = ""
        try:
            stream = self.client.chat.completions.create(
                messages=self.history,
                model=DEFAULT_MODEL,
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

    # ------------------------------------------------------------------
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
