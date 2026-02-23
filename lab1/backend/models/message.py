from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel


class Message(BaseModel):
    clientId: str
    messageId: str
    type: str
    correlationId: Optional[str]
    timestamp: str
    payload: Any

    @staticmethod
    def build(
        message_type: str,
        payload: Any,
        correlation_id: Optional[str] = None,
        message_id: Optional[str] = None,
        sender: str = "backend",
    ) -> "Message":
        return Message(
            clientId=sender,
            messageId=message_id or str(uuid4()),
            type=message_type,
            correlationId=correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload or {},
        )
