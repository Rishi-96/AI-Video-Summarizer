import pytest
import uuid
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_start_chat_session_no_summary(client, auth_headers):
    # Try with a fake summary ID
    resp = await client.post(f"/api/chat/session/start?summary_id={uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SUMMARY_NOT_FOUND"

@pytest.mark.asyncio
async def test_chat_lifecycle_mocked(client, auth_headers, mock_database):
    # 1. Manually insert a summary into mock DB
    summary_id = str(uuid.uuid4())
    user = await mock_database.users.find_one({"email": "test@example.com"})
    user_id = str(user["_id"])
    
    await mock_database.summaries.insert_one({
        "summary_id": summary_id,
        "user_id": user_id,
        "text_summary": "This is a test summary",
        "transcript": "Test transcript",
        "key_points": ["Point 1", "Point 2"]
    })

    # 2. Start session
    resp = await client.post(f"/api/chat/session/start?summary_id={summary_id}", headers=auth_headers)
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]
    assert session_id is not None

    # 3. Ask question (mock GroqChat)
    with patch("app.api.chat._get_or_rebuild_groq") as mock_get_groq:
        mock_groq = MagicMock()
        # Mocking the async ask_question method
        async def mock_ask(q): return "Mock answer for " + q
        mock_groq.ask_question = mock_ask
        mock_get_groq.return_value = mock_groq
        
        resp = await client.post(
            f"/api/chat/session/{session_id}/ask", 
            json={"question": "What is this?"}, 
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert "Mock answer" in resp.json()["answer"]

    # 4. Get messages
    resp = await client.get(f"/api/chat/session/{session_id}/messages", headers=auth_headers)
    assert resp.status_code == 200
    messages = resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
