from transformers import pipeline, BartForConditionalGeneration, BartTokenizer
from sentence_transformers import SentenceTransformer
import torch
import numpy as np
from typing import List, Dict, Optional

class VideoSummarizer:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading summarization models on {self.device}...")
        
        # Load summarization pipeline
        self.summarizer = pipeline(
            "summarization",
            model="facebook/bart-large-cnn",
            device=0 if self.device == "cuda" else -1
        )
        
        # Load sentence transformer for ranking
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("Summarization models loaded!")
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 50) -> str:
        """
        Generate summary of text
        """
        try:
            # Truncate if too long (BART has 1024 token limit)
            if len(text) > 2000:
                text = text[:2000]
            
            result = self.summarizer(
                text,
                max_length=max_length,
                min_length=min_length,
                do_sample=False
            )
            
            return result[0]['summary_text']
            
        except Exception as e:
            return f"Summarization failed: {str(e)}"
    
    def extract_key_sentences(self, text: str, num_sentences: int = 5) -> List[str]:
        """
        Extract key sentences using embeddings
        """
        # Simple sentence splitting
        sentences = [s.strip() + '.' for s in text.split('.') if len(s.strip()) > 20]
        
        if len(sentences) <= num_sentences:
            return sentences
        
        # Generate embeddings
        embeddings = self.embedder.encode(sentences)
        
        # Find most representative sentences
        centroid = np.mean(embeddings, axis=0)
        similarities = np.dot(embeddings, centroid)
        
        # Get top sentences
        top_indices = np.argsort(similarities)[-num_sentences:][::-1]
        
        return [sentences[i] for i in top_indices]
    
    def rank_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Rank video segments by importance
        """
        if not segments:
            return segments
        
        texts = [seg['text'] for seg in segments]
        
        # Generate embeddings
        embeddings = self.embedder.encode(texts)
        
        # Calculate importance scores
        # (using variance as a simple measure of information content)
        scores = np.var(embeddings, axis=1)
        
        # Normalize scores
        scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        
        # Add scores to segments
        for i, seg in enumerate(segments):
            seg['relevance_score'] = float(scores[i])
        
        # Sort by relevance
        ranked = sorted(segments, key=lambda x: x['relevance_score'], reverse=True)
        
        return ranked

# Test the model
if __name__ == "__main__":
    summarizer = VideoSummarizer()
    print("Summarizer ready!")
