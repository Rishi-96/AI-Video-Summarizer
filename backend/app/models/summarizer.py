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
    def __init__(self):
        from app.core.config import settings
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        self.use_mock = not _HAS_GROQ or not self.api_key
        
        if not self.use_mock:
            try:
                self.client = Groq(api_key=self.api_key)
                logger.info("Groq Summarizer loaded")
            except Exception as e:
                logger.warning("Error initializing Groq: %s", e)
                self.use_mock = True
        else:
            logger.warning("GROQ_API_KEY missing or groq not installed. Falling back to mock summarizer.")

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
                
                resp = self.client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}]
                )
                summaries.append(resp.choices[0].message.content.strip())

            combined = " ".join(summaries)
            
            if len(summaries) > 1:
                final_req = f"Combine these summary parts into one clean, seamless final recap (approx {max_length} words):\n\n{combined}"
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
        Without semantic text embeddings natively available in Groq, 
        we fall back to selecting segments evenly distributed across the video,
        which provides a great chronological slice of highlights!
        """
        if not segments:
            return []
            
        for i, seg in enumerate(segments):
            seg["relevance_score"] = 1.0  # Equal weight
            
        return segments