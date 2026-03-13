import pytest
import uuid
from unittest.mock import MagicMock, patch

@pytest.mark.asyncio
async def test_get_history_empty(client, auth_headers):
    resp = await client.get("/api/summarize/history", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["summaries"] == []

@pytest.mark.asyncio
async def test_summarize_local_accepted(client, auth_headers, mock_database):
    # 1. Insert fake video
    file_id = str(uuid.uuid4())
    user = await mock_database.users.find_one({"email": "test@example.com"})
    await mock_database.videos.insert_one({
        "file_id": file_id,
        "user_id": str(user["_id"]),
        "original_name": "test.mp4"
    })

    # 2. Create a temporary file to satisfy the os.path.exists check
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = tmp.name
        
    await mock_database.videos.update_one(
        {"file_id": file_id},
        {"$set": {"file_path": tmp_path}}
    )

    try:
        from app.main import app
        app.state.whisper = MagicMock()
        app.state.summarizer = MagicMock()

        resp = await client.post(
            "/api/summarize/",
            json={"file_id": file_id, "summary_ratio": 0.3},
            headers=auth_headers
        )
        assert resp.status_code == 202
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
    assert "task_id" in resp.json()
    task_id = resp.json()["task_id"]

    # 3. Check status
    resp = await client.get(f"/api/summarize/status/{task_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] in ["pending", "processing"]

@pytest.mark.asyncio
async def test_get_summary_not_found(client, auth_headers):
    resp = await client.get(f"/api/summarize/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_stream_video_not_found(client, auth_headers):
    resp = await client.get(f"/api/summarize/video/{uuid.uuid4()}/stream", headers=auth_headers)
    assert resp.status_code == 404
