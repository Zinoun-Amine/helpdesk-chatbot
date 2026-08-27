import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.schemas import ChatFeedbackCreate, ChatFeedbackResponse, ConversationResponse, ConversationSummary, MessageResponse


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_conversation(self, user_name: Optional[str] = None, user_email: Optional[str] = None) -> int:
        query = text(
            """
            INSERT INTO conversations (user_name, user_email, status)
            VALUES (:user_name, :user_email, 'active')
            RETURNING id
            """
        )
        result = await self.db.execute(query, {"user_name": user_name, "user_email": user_email})
        row = result.fetchone()
        await self.db.commit()
        return int(row._mapping["id"])

    async def update_conversation_state(self, conversation_id: int, state: str) -> None:
        await self.db.execute(
            text("UPDATE conversations SET current_state = :state, updated_at = NOW() WHERE id = :id"),
            {"state": state, "id": conversation_id},
        )
        await self.db.commit()

    async def append_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO messages (conversation_id, role, content, metadata)
                VALUES (:conversation_id, :role, :content, CAST(:metadata AS JSONB))
                """
            ),
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "metadata": json.dumps(metadata or {}),
            },
        )
        await self.db.execute(
            text("UPDATE conversations SET updated_at = NOW() WHERE id = :id"),
            {"id": conversation_id},
        )
        await self.db.commit()

    async def get_messages(self, conversation_id: int) -> List[MessageResponse]:
        result = await self.db.execute(
            text(
                """
                SELECT id, role, content, created_at AS timestamp, metadata
                FROM messages
                WHERE conversation_id = :conversation_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"conversation_id": conversation_id},
        )
        return [MessageResponse(**row._mapping) for row in result.fetchall()]

    async def get_recent_conversations(self, limit: int = 8, user_email: Optional[str] = None) -> List[ConversationSummary]:
        user_filter = "WHERE c.user_email = :user_email" if user_email else ""
        params: Dict[str, Any] = {"limit": limit}
        if user_email:
            params["user_email"] = user_email
        result = await self.db.execute(
            text(
                f"""
                SELECT c.id, c.user_name, c.user_email, c.status, c.current_state, c.created_at, c.updated_at,
                       COUNT(m.id) AS message_count
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                {user_filter}
                GROUP BY c.id
                ORDER BY c.updated_at DESC, c.created_at DESC
                LIMIT :limit
                """
            ),
            params,
        )
        return [ConversationSummary(**row._mapping) for row in result.fetchall()]

    async def get_conversation(self, conversation_id: int) -> Optional[ConversationResponse]:
        result = await self.db.execute(
            text("SELECT id FROM conversations WHERE id = :id"),
            {"id": conversation_id},
        )
        if result.fetchone() is None:
            return None
        return await self.build_response(conversation_id)

    async def add_feedback(self, payload: ChatFeedbackCreate) -> ChatFeedbackResponse:
        result = await self.db.execute(
            text(
                """
                INSERT INTO chat_feedback (conversation_id, message_id, rating, comment)
                VALUES (:conversation_id, :message_id, :rating, :comment)
                RETURNING id, conversation_id, message_id, rating, comment, created_at
                """
            ),
            payload.model_dump(),
        )
        row = result.fetchone()
        await self.db.commit()
        return ChatFeedbackResponse(**row._mapping)

    async def build_response(self, conversation_id: int) -> ConversationResponse:
        messages = await self.get_messages(conversation_id)
        return ConversationResponse(conversation_id=conversation_id, messages=messages)

    async def count_total(self, start: Optional[datetime] = None, end: Optional[datetime] = None, user_email: Optional[str] = None) -> int:
        query = "SELECT COUNT(*) AS count FROM conversations"
        params: Dict[str, Any] = {}
        filters = []
        if start:
            filters.append("created_at >= :start")
            params["start"] = start
        if end:
            filters.append("created_at < :end")
            params["end"] = end
        if user_email:
            filters.append("user_email = :user_email")
            params["user_email"] = user_email
        if filters:
            query += " WHERE " + " AND ".join(filters)
        result = await self.db.execute(text(query), params)
        row = result.fetchone()
        return int(row._mapping["count"])

    async def count_active_users(self, start: Optional[datetime] = None, end: Optional[datetime] = None, user_email: Optional[str] = None) -> int:
        query = "SELECT COUNT(DISTINCT user_email) AS count FROM conversations"
        params: Dict[str, Any] = {}
        filters = ["user_email IS NOT NULL"]
        if start:
            filters.append("updated_at >= :start")
            params["start"] = start
        if end:
            filters.append("updated_at < :end")
            params["end"] = end
        if user_email:
            filters.append("user_email = :user_email")
            params["user_email"] = user_email
        query += " WHERE " + " AND ".join(filters)
        result = await self.db.execute(text(query), params)
        row = result.fetchone()
        return int(row._mapping["count"])