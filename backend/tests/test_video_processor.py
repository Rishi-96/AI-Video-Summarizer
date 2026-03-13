"""test_video_processor.py — Unit tests for VideoProcessor."""
import pytest
import numpy as np
from app.models.video_processor import VideoProcessor

@pytest.fixture
def processor():
    return VideoProcessor()

def test_format_duration(processor):
    assert processor._format_duration(0) == "0s"
    assert processor._format_duration(59) == "59s"
    assert processor._format_duration(60) == "1m 0s"
    assert processor._format_duration(3600) == "1h 0m 0s"
    assert processor._format_duration(3661) == "1h 1m 1s"

def test_split_text_for_slides(processor):
    text = "Sentence one. Sentence two. Sentence three. Sentence four."
    # Small max_chars to force split
    chunks = processor._split_text_for_slides(text, max_chars_per_slide=30)
    assert len(chunks) >= 2
    # Check that all text is preserved (roughly)
    reconstructed = " ".join(chunks)
    assert "Sentence one" in reconstructed
    assert "Sentence four" in reconstructed

def test_split_text_empty(processor):
    assert processor._split_text_for_slides("") == [""]
    assert processor._split_text_for_slides(None) == [""]

def test_create_title_slide_returns_array(processor):
    # This might fail if fonts aren't found, but it should fallback to default
    slide = processor._create_title_slide("Test Title", "1h 2m")
    assert isinstance(slide, np.ndarray)
    assert slide.shape == (720, 1280, 3)

def test_create_closing_slide_returns_array(processor):
    slide = processor._create_closing_slide()
    assert isinstance(slide, np.ndarray)
    assert slide.shape == (720, 1280, 3)
