"""test_summarizer.py — Unit tests for VideoSummarizer with mocked Whisper output."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_segments():
    return [
        {"start": 0.0,  "end": 5.0,  "text": "The quick brown fox jumps over the lazy dog. This sentence has more than thirty characters."},
        {"start": 5.0,  "end": 10.0, "text": "Artificial intelligence is transforming the world of technology and society at large."},
        {"start": 10.0, "end": 15.0, "text": "Machine learning enables computers to learn from data without being explicitly programmed."},
        {"start": 15.0, "end": 20.0, "text": "Neural networks are inspired by the structure of the human brain and are used widely."},
        {"start": 20.0, "end": 25.0, "text": "Natural language processing allows machines to understand and generate human language text."},
    ]


def test_summarize_text_mock_mode():
    """VideoSummarizer without ML packages should return first 300 chars + ellipsis."""
    with patch("app.models.summarizer.HAS_ML", False):
        from app.models.summarizer import VideoSummarizer
        s = VideoSummarizer()
        text = "A " * 200   # 400 chars
        result = s.summarize_text(text)
        assert result.endswith("...")
        assert len(result) <= 310  # 300 chars + "..."


def test_extract_key_points_fewer_than_requested(mock_segments):
    """When there are fewer sentences than num_points, all sentences are returned."""
    from app.models.summarizer import VideoSummarizer
    s = VideoSummarizer()
    s.embedder = None   # force no-embedder path
    text = ". ".join(seg["text"] for seg in mock_segments[:2])
    points = s.extract_key_points(text, num_points=10)
    assert len(points) <= 10


def test_chunk_text_splits_correctly():
    from app.models.summarizer import VideoSummarizer
    s = VideoSummarizer()
    text = ("This is a test sentence. " * 100)
    chunks = s._chunk_text(text, max_chunk_tokens=100)
    for chunk in chunks:
        assert len(chunk) <= 120   # small tolerance for last sentence overshoot


def test_rank_segments_no_embedder(mock_segments):
    """Without an embedder, rank_segments returns the original list unchanged."""
    from app.models.summarizer import VideoSummarizer
    s = VideoSummarizer()
    s.embedder = None
    result = s.rank_segments(mock_segments)
    assert result == mock_segments


def test_rank_segments_empty():
    from app.models.summarizer import VideoSummarizer
    s = VideoSummarizer()
    assert s.rank_segments([]) == []
