import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

try:
    import torch
    import numpy as np
    HAS_ML = True
except ImportError:
    HAS_ML = False


class VideoSummarizer:
    def __init__(self):
        self.device = "cuda" if HAS_ML and torch.cuda.is_available() else "cpu"
        self.use_mock = not HAS_ML
        self.summarizer = None
        self.embedder = None

        if HAS_ML:
            try:
                from transformers import pipeline
                # Use FAST and valid summarization model
                self.summarizer = pipeline(
                    "summarization",
                    model="sshleifer/distilbart-cnn-12-6",  # Fast & Stable
                    device=0 if self.device == "cuda" else -1
                )
                logger.info("Summarizer loaded on %s", self.device)
            except Exception as e:
                logger.warning("Error loading summarizer: %s", e)
                self.use_mock = True

            try:
                from sentence_transformers import SentenceTransformer
                self.embedder = SentenceTransformer(
                    "all-MiniLM-L6-v2",
                    device=self.device
                )
                logger.info("Sentence transformer loaded")
            except Exception as e:
                logger.warning("Error loading sentence transformer: %s", e)
                self.embedder = None
    # -------------------------------
    # TEXT CHUNKING (CRITICAL FIX)
    # -------------------------------
    def _chunk_text(self, text: str, max_chunk_tokens: int = 800) -> List[str]:
        sentences = text.split(". ")
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chunk_tokens:
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

        if self.use_mock:
            return text[:300] + "..."

        try:
            chunks = self._chunk_text(text)
            summaries = []

            for chunk in chunks:
                result = self.summarizer(
                    chunk,
                    max_length=max_length,
                    min_length=40,
                    do_sample=False,
                    num_beams=4
                )
                summaries.append(result[0]["summary_text"])

            # Final summary of summaries
            combined = " ".join(summaries)

            if len(summaries) > 1:
                final = self.summarizer(
                    combined,
                    max_length=max_length,
                    min_length=40,
                    do_sample=False
                )
                return final[0]["summary_text"]

            return combined

        except Exception as e:
            logger.warning("Summarization failed: %s", e)
            return text[:300] + "..."

    # -------------------------------
    # KEY POINT EXTRACTION
    # -------------------------------
    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:

        sentences = [
            s.strip() + "."
            for s in text.split(".")
            if len(s.strip()) > 30
        ]

        if len(sentences) <= num_points:
            return sentences

        if self.embedder is None:
            return sentences[:num_points]

        try:
            embeddings = self.embedder.encode(
                sentences,
                batch_size=16,
                show_progress_bar=False
            )

            centroid = np.mean(embeddings, axis=0)
            similarities = np.dot(embeddings, centroid)

            top_indices = np.argsort(similarities)[-num_points:][::-1]

            return [sentences[i] for i in top_indices]

        except Exception as e:
            logger.warning("Key point extraction failed: %s", e)
            return sentences[:num_points]

    # -------------------------------
    # SEGMENT RANKING
    # -------------------------------
    def rank_segments(self, segments: List[Dict]) -> List[Dict]:

        if not segments or self.embedder is None:
            return segments

        try:
            texts = [seg.get("text", "") for seg in segments]

            embeddings = self.embedder.encode(
                texts,
                batch_size=16,
                show_progress_bar=False
            )

            scores = np.var(embeddings, axis=1)

            if scores.max() > scores.min():
                scores = (scores - scores.min()) / (scores.max() - scores.min())
            else:
                scores = np.ones_like(scores)

            for i, seg in enumerate(segments):
                seg["relevance_score"] = float(scores[i])

            return sorted(
                segments,
                key=lambda x: x["relevance_score"],
                reverse=True
            )

        except Exception as e:
            logger.warning("Segment ranking failed: %s", e)
            return segments