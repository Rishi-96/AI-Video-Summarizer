from transformers import pipeline
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from typing import List, Dict, Optional

class VideoSummarizer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.use_mock = False
        
        try:
            # Load summarization pipeline
            self.summarizer = pipeline(
                "summarization",
                model="facebook/bart-small-cnn",
                device=0 if self.device == "cuda" else -1
            )
            print(f"✅ Summarizer loaded on {self.device}")
        except Exception as e:
            print(f"⚠️ Error loading summarizer: {e}")
            self.use_mock = True
        
        try:
            # Load sentence transformer
            self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Sentence transformer loaded")
        except Exception as e:
            print(f"⚠️ Error loading sentence transformer: {e}")
            self.embedder = None
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """Generate summary of text"""
        
        # Mock mode
        if self.use_mock:
            if len(text) > 200:
                return text[:200] + "... [Summary would be generated here]"
            return text
        
        try:
            # Truncate if too long
            if len(text) > 2000:
                text = text[:2000]
            
            result = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,
                num_beams=4,
                length_penalty=2.0
            )
            
            return result[0]['summary_text']
            
        except Exception as e:
            print(f"Summarization failed: {e}")
            return text[:200] + "..."
    
    def extract_key_points(self, text: str, num_points: int = 5) -> List[str]:
        """Extract key points using embeddings"""
        
        # Simple sentence splitting
        sentences = [s.strip() + '.' for s in text.split('.') if len(s.strip()) > 20]
        
        if len(sentences) <= num_points:
            return sentences
        
        if self.embedder is None:
            return sentences[:num_points]
        
        try:
            # Generate embeddings
            embeddings = self.embedder.encode(sentences)
            
            # Find most representative sentences
            centroid = np.mean(embeddings, axis=0)
            similarities = np.dot(embeddings, centroid)
            
            # Get top sentences
            top_indices = np.argsort(similarities)[-num_points:][::-1]
            
            return [sentences[i] for i in top_indices]
            
        except Exception as e:
            print(f"Key point extraction failed: {e}")
            return sentences[:num_points]
    
    def rank_segments(self, segments: List[Dict]) -> List[Dict]:
        """Rank video segments by importance"""
        
        if not segments:
            return segments
        
        if self.embedder is None:
            # Simple ranking based on position
            for i, seg in enumerate(segments):
                seg['relevance_score'] = 1.0 - (i / len(segments))
            return segments
        
        try:
            texts = [seg.get('text', '') for seg in segments]
            
            # Generate embeddings
            embeddings = self.embedder.encode(texts)
            
            # Calculate importance scores (using variance)
            scores = np.var(embeddings, axis=1)
            
            # Normalize scores
            if scores.max() > scores.min():
                scores = (scores - scores.min()) / (scores.max() - scores.min())
            else:
                scores = np.ones_like(scores)
            
            # Add scores to segments
            for i, seg in enumerate(segments):
                seg['relevance_score'] = float(scores[i])
            
            # Sort by relevance
            ranked = sorted(segments, key=lambda x: x['relevance_score'], reverse=True)
            
            return ranked
            
        except Exception as e:
            print(f"Ranking failed: {e}")
            return segments