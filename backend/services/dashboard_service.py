from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.fallback_provider import FallbackProvider
from models.schemas import DashboardResponse, ProviderStats
from services.conversation_service import ConversationService


class DashboardService:
    def __init__(self, db: AsyncSession, llm_provider: Optional[FallbackProvider] = None):
        self.db = db
        self.llm_provider = llm_provider
        self.conversations = ConversationService(db)

    def _date_window(self, period: str, start: Optional[datetime], end: Optional[datetime]) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        if start and end:
            return start, end
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "7d":
            start = now - timedelta(days=7)
        elif period == "30d":
            start = now - timedelta(days=30)
        elif period == "90d":
            start = now - timedelta(days=90)
        else:
            start = now - timedelta(days=30)
        return start, now

    async def get_dashboard(self, period: str = "30d", start: Optional[datetime] = None, end: Optional[datetime] = None, user_email: Optional[str] = None) -> DashboardResponse:
        start_date, end_date = self._date_window(period, start, end)
        owner_filter = " AND user_email = :user_email" if user_email else ""
        owner_params = {"user_email": user_email} if user_email else {}
        message_owner_filter = (
            " AND conversation_id IN (SELECT id FROM conversations WHERE user_email = :user_email)"
            if user_email else ""
        )

        ticket_counts = await self.db.execute(
            text(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE COALESCE(status_label, status) IN ('Open', 'open', 'nouveau')) AS open_count,
                    COUNT(*) FILTER (WHERE COALESCE(status_label, status) = 'In Progress') AS in_progress_count,
                    COUNT(*) FILTER (WHERE COALESCE(status_label, status) IN ('Resolved', 'Closed')) AS resolved_count,
                    COUNT(*) FILTER (WHERE COALESCE(status_label, status) = 'Closed') AS closed_count,
                    COUNT(*) FILTER (WHERE created_at >= :start_date AND created_at < :end_date) AS recent_count
                FROM tickets
                WHERE TRUE{owner_filter}
                """
            ),
            {"start_date": start_date, "end_date": end_date, **owner_params},
        )
        ticket_counts_row = ticket_counts.fetchone()._mapping

        avg_resolution = await self.db.execute(
            text(
                f"""
                SELECT AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, solved_at) - created_at)) / 3600.0) AS avg_hours
                FROM tickets
                WHERE COALESCE(resolved_at, solved_at) IS NOT NULL{owner_filter}
                """
            ), owner_params
        )
        avg_resolution_hours = avg_resolution.fetchone()._mapping["avg_hours"] or 0.0

        conversations_total = await self.conversations.count_total(start_date, end_date, user_email)
        active_users = await self.conversations.count_active_users(start_date, end_date, user_email)
        recent_conversations = await self.conversations.get_recent_conversations(limit=8, user_email=user_email)

        ticket_status = await self.db.execute(
            text(
                f"""
                SELECT COALESCE(status_label, status) AS status, COUNT(*) AS count
                FROM tickets
                WHERE TRUE{owner_filter}
                GROUP BY 1
                ORDER BY count DESC
                """
            ), owner_params
        )
        ticket_priority = await self.db.execute(
            text(
                f"""
                SELECT COALESCE(priority_label, 'Medium') AS priority, COUNT(*) AS count
                FROM tickets
                WHERE TRUE{owner_filter}
                GROUP BY 1
                ORDER BY count DESC
                """
            ), owner_params
        )

        activity = await self.db.execute(
            text(
                f"""
                SELECT DATE_TRUNC('day', created_at) AS day, COUNT(*) AS count
                FROM messages
                                WHERE created_at >= :start_date AND created_at < :end_date{message_owner_filter}
                GROUP BY 1
                ORDER BY 1 ASC
                """
            ),
            {"start_date": start_date, "end_date": end_date, **owner_params},
        )

        ticket_activity = await self.db.execute(
            text(
                f"""
                SELECT DATE_TRUNC('day', created_at) AS day, COUNT(*) AS count
                FROM tickets
                WHERE created_at >= :start_date AND created_at < :end_date{owner_filter}
                GROUP BY 1
                ORDER BY 1 ASC
                """
            ),
            {"start_date": start_date, "end_date": end_date, **owner_params},
        )

        provider_stats = []
        total_requests = 0
        if self.llm_provider and hasattr(self.llm_provider, "get_stats_snapshot"):
            snapshot = self.llm_provider.get_stats_snapshot()
            total_requests = sum(item.get("requests", 0) for item in snapshot.values()) or 1
            for provider_name, stats in snapshot.items():
                requests = stats.get("requests", 0)
                avg_ms = (stats.get("latency_total_ms", 0.0) / requests) if requests else 0.0
                provider_stats.append(
                    ProviderStats(
                        provider=provider_name,
                        label=stats.get("label", provider_name.title()),
                        requests=requests,
                        successes=stats.get("success", 0),
                        errors=stats.get("errors", 0),
                        fallbacks=stats.get("fallback_triggered", 0),
                        avg_response_ms=round(avg_ms, 2),
                        utilization=round((requests / total_requests) * 100, 2),
                    )
                )

        return DashboardResponse(
            totals={
                "conversations": conversations_total,
                "tickets": int(ticket_counts_row["total"] or 0),
                "open_tickets": int(ticket_counts_row["open_count"] or 0),
                "in_progress_tickets": int(ticket_counts_row["in_progress_count"] or 0),
                "resolved_tickets": int(ticket_counts_row["resolved_count"] or 0),
                "closed_tickets": int(ticket_counts_row["closed_count"] or 0),
                "resolution_rate": round(((ticket_counts_row["resolved_count"] or 0) / max(ticket_counts_row["total"] or 1, 1)) * 100, 2),
                "avg_resolution_hours": round(float(avg_resolution_hours or 0.0), 2),
                "active_users": active_users,
                "recent_tickets": int(ticket_counts_row["recent_count"] or 0),
            },
            charts={
                "activity": [dict(row._mapping) for row in activity.fetchall()],
                "ticket_activity": [dict(row._mapping) for row in ticket_activity.fetchall()],
                "ticket_status": [dict(row._mapping) for row in ticket_status.fetchall()],
                "ticket_priority": [dict(row._mapping) for row in ticket_priority.fetchall()],
            },
            recent_conversations=recent_conversations,
            llm_providers=provider_stats,
        )
