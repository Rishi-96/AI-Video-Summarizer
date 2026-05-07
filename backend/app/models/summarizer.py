import logging
import os
import json
from typing import List, Dict
import httpx
from app.core.config import settings
from app.core.constants import (
    GROQ_SUMMARIZATION_MODEL,
    OLLAMA_MODEL,
    OLLAMA_GENERATE_URL,
    OLLAMA_TAGS_URL,
    HF_SUMMARIZATION_MODEL,
    TEXT_CHUNK_MAX_CHARS,
)

try:
    from groq import Groq
    _HAS_GROQ = True
except ImportError:
    _HAS_GROQ = False

logger = logging.getLogger(__name__)

class VideoSummarizer:
    _hf_summarizer = None

    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        self.use_mock = not _HAS_GROQ or not self.api_key
        
        if not self.use_mock:
            try:
                _disable_ssl = os.environ.get("DISABLE_SSL_VERIFY", "").lower() == "true"
                http_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
                http_client = httpx.Client(
                    proxy=http_proxy,
                    verify=not _disable_ssl,
                )
                
                # Try Ollama first if it's running, else fallback to Groq
                try:
                    ollama_check = httpx.get(OLLAMA_TAGS_URL, timeout=1.0)
                    if ollama_check.status_code == 200:
                        self.use_ollama = True
                        self.ollama_url = OLLAMA_GENERATE_URL
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
                logger.info("Loading HuggingFace summarization pipeline (%s)...", HF_SUMMARIZATION_MODEL)
                cls._hf_summarizer = pipeline("summarization", model=HF_SUMMARIZATION_MODEL)
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
    def _chunk_text(self, text: str, max_chunk_chars: int = TEXT_CHUNK_MAX_CHARS) -> List[str]:
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
    def summarize_text(self, text: str, max_length: int = 400) -> str:
        if self.use_mock or not text.strip():
            return text[:500] + "..."

        try:
            chunks = self._chunk_text(text)
            summaries = []

            for chunk in chunks:
                prompt = (
                    f"You are an expert video content summarizer. Provide a comprehensive, "
                    f"accurate, and detailed summary of the following video transcript. "
                    f"Requirements:\n"
                    f"1. Cover ALL major topics, arguments, and conclusions discussed.\n"
                    f"2. Preserve important names, numbers, dates, and technical terms exactly as stated.\n"
                    f"3. Maintain the logical flow and structure of the content.\n"
                    f"4. The summary should be approximately {max_length} words long.\n"
                    f"5. Write in clear, professional language that is easy to understand.\n"
                    f"6. Do NOT add information that is not in the transcript.\n\n"
                    f"Transcript:\n{chunk}"
                )
                
                if self.use_ollama:
                    resp = httpx.post(self.ollama_url, json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False
                    }, timeout=90.0)
                    summaries.append(resp.json().get("response", "").strip())
                else:
                    resp = self.client.chat.completions.create(
                        model=GROQ_SUMMARIZATION_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.2,
                    )
                    summaries.append(resp.choices[0].message.content.strip())

            combined = " ".join(summaries)
            
            if len(summaries) > 1:
                final_req = (
                    f"Combine the following summary sections into one unified, coherent, "
                    f"and comprehensive summary (approximately {max_length} words). "
                    f"Remove any redundancy, ensure smooth transitions between topics, "
                    f"and preserve all key information accurately:\n\n{combined}"
                )
                if self.use_ollama:
                    resp = httpx.post(self.ollama_url, json={
                        "model": OLLAMA_MODEL,
                        "prompt": final_req,
                        "stream": False
                    }, timeout=90.0)
                    return resp.json().get("response", "").strip()
                else:
                    final = self.client.chat.completions.create(
                        model=GROQ_SUMMARIZATION_MODEL,
                        messages=[{"role": "user", "content": final_req}],
                        temperature=0.2,
                    )
                    return final.choices[0].message.content.strip()

            return combined

        except Exception as e:
            logger.warning("Groq Summarization failed: %s", e)
            return text[:500] + "..."

    # -------------------------------
    # KEY POINT EXTRACTION
    # -------------------------------
    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        if self.use_mock or not text.strip():
            return [s.strip() + "." for s in text.split(".") if len(s.strip()) > 30][:num_points]

        try:
            # We only need the first big chunk to extract decent high-level points
            chunk = text[:TEXT_CHUNK_MAX_CHARS] 
            prompt = f"Extract the {num_points} most important key points from the following video transcript. These should be detailed but clear bullet points that represent the core value of the content. Return ONLY a valid JSON array of strings, with no other formatting or markdown.\n\nTranscript: {chunk}"
            
            if self.use_ollama:
                resp = httpx.post(self.ollama_url, json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                }, timeout=60.0)
                raw = resp.json().get("response", "").strip()
            else:
                resp = self.client.chat.completions.create(
                    model=GROQ_SUMMARIZATION_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                raw = resp.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting 
            if raw.startswith("```json"):
                raw = raw[7:]
            if raw.startswith("```"):
                raw = raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            
            points = json.loads(raw.strip())
            return points[:num_points]
        except Exception as e:
            logger.warning("Groq Key point extraction failed: %s", e)
            return [text[:100] + "..."]

    # -------------------------------
    # SEGMENT RANKING (TF-IDF + TextRank)
    # -------------------------------
    def rank_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Rank transcript segments by importance using TF-IDF + TextRank.

        Scoring combines:
          - TextRank centrality (how similar a segment is to others)
          - Text density (longer, more content-rich segments score higher)
          - Transcription confidence (higher confidence = more trustworthy)
        """
        if not segments:
            return []

        texts = [seg.get("text", "").strip() for seg in segments]

        # Filter out empty segments
        valid_indices = [i for i, t in enumerate(texts) if len(t) > 10]
        if len(valid_indices) < 2:
            for seg in segments:
                seg["relevance_score"] = 1.0
            return segments

        valid_texts = [texts[i] for i in valid_indices]

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            # Build TF-IDF matrix
            vectorizer = TfidfVectorizer(
                stop_words="english",
                max_features=500,
                min_df=1,
                max_df=0.95,
            )
            tfidf_matrix = vectorizer.fit_transform(valid_texts)

            # TextRank: cosine similarity graph → sum of edge weights
            sim_matrix = cosine_similarity(tfidf_matrix)
            np.fill_diagonal(sim_matrix, 0)

            # Iterative TextRank (simplified PageRank)
            n = len(valid_texts)
            scores = np.ones(n) / n
            damping = 0.85
            for _ in range(10):  # 10 iterations is sufficient for convergence
                row_sums = sim_matrix.sum(axis=1, keepdims=True)
                row_sums[row_sums == 0] = 1  # avoid division by zero
                norm_matrix = sim_matrix / row_sums
                scores = (1 - damping) / n + damping * norm_matrix.T @ scores

            # Normalize to 0-1
            if scores.max() > scores.min():
                scores = (scores - scores.min()) / (scores.max() - scores.min())
            else:
                scores = np.ones(n)

            # Apply scores back to original segments
            for seg in segments:
                seg["relevance_score"] = 0.1  # default low score for invalid segments

            for idx_in_valid, orig_idx in enumerate(valid_indices):
                seg = segments[orig_idx]
                textrank_score = float(scores[idx_in_valid])

                # Text density bonus (longer segments likely contain more info)
                text_len = len(seg.get("text", ""))
                density_bonus = min(text_len / 200.0, 1.0)  # cap at 1.0

                # Confidence bonus from transcription
                confidence = seg.get("confidence", 1.0)

                # Weighted combination
                seg["relevance_score"] = (
                    0.60 * textrank_score +
                    0.25 * density_bonus +
                    0.15 * confidence
                )

            # Sort by relevance (highest first)
            return sorted(segments, key=lambda s: s["relevance_score"], reverse=True)

        except Exception as e:
            logger.warning("TF-IDF ranking failed, falling back to equal weight: %s", e)
            for seg in segments:
                seg["relevance_score"] = 1.0
            return segments