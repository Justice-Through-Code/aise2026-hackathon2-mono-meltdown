"""
Content Service - Handles content upload, search, and listing.

Bug fixes applied:
- Content upload now writes to persistent database (was using in-memory DB)
- Content search queries the database directly instead of stale cache
- File upload now actually persists content to the database
- Cache invalidation implemented properly
"""

import json
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from services.shared.auth import verify_token
from services.shared.database import get_connection
from services.shared.models import ContentSearch, ContentUpload

router = APIRouter(tags=["content"])


@router.post("/content/upload")
async def upload_content(content: ContentUpload, user: dict = Depends(verify_token)):
    """Upload lesson content. Fixed: now persists to the actual database."""
    user_id = user["user_id"]
    content_id = str(uuid.uuid4())
    metadata_json = json.dumps(content.metadata) if content.metadata else None

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO content (id, title, body, content_type, metadata, uploaded_by, is_indexed) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (content_id, content.title, content.body, content.content_type, metadata_json, user_id),
        )
        conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content upload failed: {str(e)}")
    finally:
        conn.close()

    return {
        "message": "Content uploaded successfully",
        "content_id": content_id,
        "title": content.title,
        "status": "indexed",
    }


@router.post("/content/upload-file")
async def upload_content_file(
    file: UploadFile = File(...),
    user: dict = Depends(verify_token),
):
    """Upload content from a JSON file. Fixed: now actually persists all items."""
    user_id = user["user_id"]

    try:
        file_content = await file.read()
        data = json.loads(file_content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file")

    conn = get_connection()
    try:
        if isinstance(data, list):
            processed = 0
            for item in data:
                content_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO content (id, title, body, content_type, metadata, uploaded_by, is_indexed) "
                    "VALUES (?, ?, ?, ?, ?, ?, 1)",
                    (
                        content_id,
                        item.get("title", "Untitled"),
                        item.get("body", ""),
                        item.get("content_type", "lesson"),
                        json.dumps(item.get("metadata")) if item.get("metadata") else None,
                        user_id,
                    ),
                )
                processed += 1
            conn.commit()
            return {
                "message": f"Successfully uploaded {processed} content items",
                "count": processed,
                "status": "indexed",
            }
        elif isinstance(data, dict):
            content_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO content (id, title, body, content_type, metadata, uploaded_by, is_indexed) "
                "VALUES (?, ?, ?, ?, ?, ?, 1)",
                (
                    content_id,
                    data.get("title", "Untitled"),
                    data.get("body", ""),
                    data.get("content_type", "lesson"),
                    json.dumps(data.get("metadata")) if data.get("metadata") else None,
                    user_id,
                ),
            )
            conn.commit()
            return {
                "message": "Content uploaded successfully",
                "content_id": content_id,
                "status": "indexed",
            }
        else:
            raise HTTPException(status_code=400, detail="JSON must be an object or array")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    finally:
        conn.close()


@router.post("/content/search")
async def search_content(search: ContentSearch, user: dict = Depends(verify_token)):
    """Search content by keyword matching. Fixed: queries database directly instead of stale cache."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, title, body, content_type, metadata FROM content WHERE is_indexed = 1"
    )
    rows = c.fetchall()
    conn.close()

    query_lower = search.query.lower()
    query_words = set(query_lower.split())

    results = []
    for row in rows:
        title_lower = (row["title"] or "").lower()
        body_lower = (row["body"] or "").lower()
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        score = 0
        for word in query_words:
            if word in title_lower:
                score += 10
            if word in body_lower:
                score += 1
            tags = metadata.get("tags", [])
            if any(word in tag for tag in tags):
                score += 5

        if score > 0:
            body_text = row["body"] or ""
            results.append({
                "id": row["id"],
                "title": row["title"],
                "body": body_text[:200] + "..." if len(body_text) > 200 else body_text,
                "content_type": row["content_type"],
                "score": score,
                "metadata": metadata,
            })

    results.sort(key=lambda x: x["score"], reverse=True)

    # If no keyword matches, return all content up to the limit
    if not results:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT id, title, body, content_type, metadata FROM content "
            "WHERE is_indexed = 1 LIMIT ?",
            (search.limit,),
        )
        fallback_rows = c.fetchall()
        conn.close()

        for row in fallback_rows:
            body_text = row["body"] or ""
            results.append({
                "id": row["id"],
                "title": row["title"],
                "body": body_text[:200] + "..." if len(body_text) > 200 else body_text,
                "content_type": row["content_type"],
                "score": 0,
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            })

    return {
        "results": results[:search.limit],
        "total": len(results),
        "query": search.query,
        "source": "database",
    }


@router.get("/content")
async def list_content(user: dict = Depends(verify_token)):
    """List all content from the database."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, title, body, content_type, metadata, created_at "
        "FROM content ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()

    content_list = [
        {
            "id": row["id"],
            "title": row["title"],
            "body": row["body"][:200] + "..." if row["body"] and len(row["body"]) > 200 else row["body"],
            "content_type": row["content_type"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"],
        }
        for row in rows
    ]

    return {"content": content_list, "total": len(content_list)}
