"""
Chat Service - Handles conversation with the Groq LLM API and chat history.

Responsibilities:
- Sending messages to the Groq API with conversation context
- Storing and retrieving chat history
- Building system prompts with content context
"""

import json
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException

from services.shared.auth import verify_token
from services.shared.config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL, MAX_CHAT_HISTORY
from services.shared.database import get_connection
from services.shared.models import ChatMessage

router = APIRouter(tags=["chat"])


def _get_system_prompt() -> str:
    """Build the system prompt for the chatbot, including content context from the database."""
    base_prompt = """You are AISE ASK, a helpful AI assistant for the AI Safety and Engineering (AISE) fellowship program.
You help fellows with questions about:
- The AISE curriculum and schedule
- AI safety concepts (alignment, interpretability, robustness)
- Prompt engineering techniques
- Building AI agents
- Technical concepts covered in the program
- Program logistics and schedules

Be friendly, concise, and helpful. If you don't know something specific about the AISE program,
say so honestly rather than making things up. You can still help with general AI/ML questions.

Keep responses focused and practical. Fellows are busy learning - respect their time."""

    conn = None
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT title, body FROM content WHERE is_indexed = 1 LIMIT 5"
        )
        rows = c.fetchall()

        if rows:
            content_context = "\n\nHere is some reference content from the AISE program:\n"
            for row in rows:
                content_context += f"\n--- {row['title']} ---\n{row['body']}\n"
            base_prompt += content_context
    except Exception:
        pass  # If content lookup fails, proceed without context
    finally:
        if conn:
            conn.close()

    return base_prompt


@router.post("/chat")
async def chat(message: ChatMessage, user: dict = Depends(verify_token)):
    """Send a message to AISE ASK and get a response from the Groq LLM."""
    user_id = user["user_id"]

    if not GROQ_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="GROQ_API_KEY not configured. Set it as an environment variable.",
        )

    session_id = message.session_id or str(uuid.uuid4())

    # Load chat history for this session
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT message, response FROM chat_history "
            "WHERE user_id = ? AND session_id = ? ORDER BY timestamp DESC LIMIT ?",
            (user_id, session_id, MAX_CHAT_HISTORY),
        )
        history_rows = c.fetchall()
    finally:
        conn.close()

    # Build messages array for Groq API
    messages = [{"role": "system", "content": _get_system_prompt()}]

    for row in reversed(history_rows):
        messages.append({"role": "user", "content": row["message"]})
        messages.append({"role": "assistant", "content": row["response"]})

    messages.append({"role": "user", "content": message.message})

    # Call Groq API
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"LLM API error: {response.status_code}",
                )

            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]
            tokens_used = result.get("usage", {}).get("total_tokens", 0)

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="LLM API timeout")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Chat processing failed")

    # Save to database
    chat_id = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO chat_history (id, user_id, message, response, session_id, tokens_used) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, message.message, assistant_message, session_id, tokens_used),
        )
        conn.commit()
    except Exception:
        pass  # Non-critical: chat still works even if history save fails
    finally:
        conn.close()

    return {
        "response": assistant_message,
        "session_id": session_id,
        "chat_id": chat_id,
        "tokens_used": tokens_used,
    }


@router.get("/chat/history")
async def get_chat_history(
    session_id: Optional[str] = None,
    limit: int = 20,
    user: dict = Depends(verify_token),
):
    """Get chat history for the authenticated user."""
    user_id = user["user_id"]

    conn = get_connection()
    try:
        c = conn.cursor()

        if session_id:
            c.execute(
                "SELECT id, message, response, timestamp, session_id, tokens_used "
                "FROM chat_history WHERE user_id = ? AND session_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (user_id, session_id, limit),
            )
        else:
            c.execute(
                "SELECT id, message, response, timestamp, session_id, tokens_used "
                "FROM chat_history WHERE user_id = ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            )

        rows = c.fetchall()
    finally:
        conn.close()

    history = [
        {
            "id": row["id"],
            "message": row["message"],
            "response": row["response"],
            "timestamp": row["timestamp"],
            "session_id": row["session_id"],
            "tokens_used": row["tokens_used"],
        }
        for row in rows
    ]

    return {"history": history, "count": len(history)}
