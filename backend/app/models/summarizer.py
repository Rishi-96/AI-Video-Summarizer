import logging
import os
import json
from typing import List, Dict

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

logger = logging.getLogger(__name__)

class VideoSummarizer:
    _hf_summarizer = None

    def __init__(self):
        from app.core.config import settings
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        self.use_mock = not _HAS_GROQ or not self.api_key
        
        if not self.use_mock:
            try:
                import httpx
                http_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
                http_client = httpx.Client(proxy=http_proxy, verify=False) if http_proxy else httpx.Client(verify=False)
                
                # Try Ollama first if it's running, else fallback to Groq
                try:
                    ollama_check = httpx.get("http://localhost:11434/api/tags", timeout=1.0)
                    if ollama_check.status_code == 200:
                        self.use_ollama = True
                        self.ollama_url = "http://localhost:11434/api/generate"
                        logger.info("Ollama Summarizer detected and loaded")
                    else:
                        self.use_ollama = False
                except Exception:
                    self.use_ollama = False

                if not self.use_ollama:
                    self.client = Groq(api_key=self.api_key, http_client=http_client)
                    logger.info("Groq Summarizer loaded")
                
            except Exception as e:
                logger.warning("Error initializing AI backend: %s", e)
                self.use_mock = True
        else:
            logger.warning("GROQ_API_KEY missing or groq not installed. Falling back to mock summarizer.")

    @classmethod
    def get_hf_summarizer(cls):
        if cls._hf_summarizer is None:
            try:
                from transformers import pipeline
                logger.info("Loading HuggingFace summarization pipeline (sshleifer/distilbart-cnn-12-6)...")
                cls._hf_summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")
            except Exception as e:
                logger.error(f"Failed to load HuggingFace summarizer: {e}")
        return cls._hf_summarizer

    def summarize_hf(self, text: str, max_length: int = 150) -> str:
        """Summarize text using local HuggingFace transformers pipeline."""
        summarizer = self.get_hf_summarizer()
        if not summarizer or not text.strip():
            return text[:300] + "..."
        try:
            # Simple chunking for HF model limits (max 1024 tokens)
            chunk = text[:3000]
            result = summarizer(chunk, max_length=max_length, min_length=30, do_sample=False)
            return result[0]['summary_text']
        except Exception as e:
            logger.error(f"HF Summarization error: {e}")
            return text[:300] + "..."

    # -------------------------------
    # TEXT CHUNKING
    # -------------------------------
    def _chunk_text(self, text: str, max_chunk_chars: int = 15000) -> List[str]:
        # Groq llama3 supports 8k tokens (~32k chars), 15k chars is very safe
        sentences = text.split(". ")
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_chars:
                current_chunk += sentence + ". "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "

        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks

    # -------------------------------
    # SUMMARIZATION
    # -------------------------------
    def summarize_text(self, text: str, max_length: int = 150) -> str:
        if self.use_mock or not text.strip():
            return text[:300] + "..."

        try:
            chunks = self._chunk_text(text)
            summaries = []

            for chunk in chunks:
                prompt = f"Please provide a concise and highly accurate summary of the following video transcript. The summary should be approximately {max_length} words long.\n\nTranscript: {chunk}"
                
                if self.use_ollama:
                    import httpx
                    resp = httpx.post(self.ollama_url, json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False
                    }, timeout=60.0)
                    summaries.append(resp.json().get("response", "").strip())
                else:
                    resp = self.client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    summaries.append(resp.choices[0].message.content.strip())

            combined = " ".join(summaries)
            
            if len(summaries) > 1:
                final_req = f"Combine these summary parts into one clean, seamless final recap (approx {max_length} words):\n\n{combined}"
                if self.use_ollama:
                    import httpx
                    resp = httpx.post(self.ollama_url, json={
                        "model": "llama3",
                        "prompt": final_req,
                        "stream": False
                    }, timeout=60.0)
                    return resp.json().get("response", "").strip()
                else:
                    final = self.client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": final_req}]
                    )
                    return final.choices[0].message.content.strip()

            return combined

        except Exception as e:
            logger.warning("Groq Summarization failed: %s", e)
            return text[:300] + "..."

    # -------------------------------
    # KEY POINT EXTRACTION
    # -------------------------------
    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        if self.use_mock or not text.strip():
            return [s.strip() + "." for s in text.split(".") if len(s.strip()) > 30][:num_points]

        try:
            # We only need the first big chunk to extract decent high-level points
            chunk = text[:15000] 
            prompt = f"Extract exactly {num_points} key bullet points from the following video transcript. Return ONLY a valid JSON array of strings, with no other formatting or markdown.\n\nTranscript: {chunk}"
            
            if self.use_ollama:
                import httpx
                resp = httpx.post(self.ollama_url, json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                }, timeout=60.0)
                raw = resp.json().get("response", "").strip()
            else:
                resp = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                raw = resp.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting 
            if raw.startswith("```json"): raw = raw[7:]
            if raw.startswith("```"): raw = raw[3:]
            if raw.endswith("```"): raw = raw[:-3]
            
            points = json.loads(raw.strip())
            return points[:num_points]
        except Exception as e:
            logger.warning("Groq Key point extraction failed: %s", e)
            return [text[:100] + "..."]

    # -------------------------------
    # SEGMENT RANKING
    # -------------------------------
    def rank_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Rank segments based on relevance or other metrics.
        Currently returns segments with equal weight, allowing the caller 
        to decide on distribution/slicing (e.g., evenly across the video).
        """
        if not segments:
            return []
            
        for seg in segments:
            seg["relevance_score"] = 1.0  # Equal weight
            
        return segments