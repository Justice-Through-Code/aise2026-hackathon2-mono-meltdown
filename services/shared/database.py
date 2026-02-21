"""
Shared database utilities for AISE ASK microservices.
Handles initialization, connection management, and seed data.
"""

import json
import sqlite3
import uuid

from .config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize all database tables."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            role TEXT DEFAULT 'fellow'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            tokens_used INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS content (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            content_type TEXT DEFAULT 'lesson',
            metadata TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            uploaded_by TEXT,
            is_indexed INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def seed_default_content():
    """Seed default content if the content table is empty."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM content")
    count = c.fetchone()[0]

    if count == 0:
        default_content = [
            {
                "id": str(uuid.uuid4()),
                "title": "Introduction to AI Safety",
                "body": (
                    "AI Safety is a field dedicated to ensuring that artificial intelligence "
                    "systems are developed and deployed in ways that are safe, beneficial, and "
                    "aligned with human values. Key topics include alignment, interpretability, "
                    "robustness, and governance. The AISE program covers these fundamentals "
                    "across 12 weeks of intensive study."
                ),
                "content_type": "lesson",
                "metadata": json.dumps({
                    "week": 1, "module": "foundations",
                    "tags": ["ai-safety", "intro", "alignment"],
                }),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Prompt Engineering Fundamentals",
                "body": (
                    "Prompt engineering is the practice of designing and refining inputs to "
                    "large language models to achieve desired outputs. Techniques include "
                    "zero-shot prompting, few-shot prompting, chain-of-thought reasoning, and "
                    "system prompt design. Fellows will practice these techniques throughout "
                    "the AISE program with hands-on exercises."
                ),
                "content_type": "lesson",
                "metadata": json.dumps({
                    "week": 2, "module": "prompt-engineering",
                    "tags": ["prompts", "llm", "techniques"],
                }),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Building AI Agents",
                "body": (
                    "AI Agents are systems that use LLMs as reasoning engines to take actions, "
                    "use tools, and accomplish goals autonomously. Key concepts include tool use, "
                    "planning, memory systems, and evaluation. The AISE program dedicates weeks "
                    "5-8 to building increasingly sophisticated agent systems."
                ),
                "content_type": "lesson",
                "metadata": json.dumps({
                    "week": 5, "module": "agents",
                    "tags": ["agents", "tools", "planning"],
                }),
            },
            {
                "id": str(uuid.uuid4()),
                "title": "AISE Program Schedule",
                "body": (
                    "Week 1-2: Foundations of AI Safety and Ethics. Week 3-4: Prompt Engineering "
                    "and LLM APIs. Week 5-8: Building AI Agents and Tool Use. Week 9-10: "
                    "Evaluation and Red Teaming. Week 11-12: Capstone Projects and Presentations. "
                    "All sessions are held Monday-Friday, 9am-5pm ET."
                ),
                "content_type": "schedule",
                "metadata": json.dumps({"type": "schedule", "version": "2025-fall"}),
            },
        ]
        for item in default_content:
            c.execute(
                "INSERT INTO content (id, title, body, content_type, metadata, is_indexed) "
                "VALUES (?, ?, ?, ?, ?, 1)",
                (item["id"], item["title"], item["body"], item["content_type"], item["metadata"]),
            )
        conn.commit()

    conn.close()
