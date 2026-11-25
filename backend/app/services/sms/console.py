"""Default SMS driver: logs the message to the console instead of sending it.

Lets the full registration -> SMS -> delivery_status workflow be exercised
without any real provider credentials.
"""
import logging
import uuid

from app.services.sms.base import ProviderResult

logger = logging.getLogger("sms.console")


class ConsoleSmsProvider:
    name = "console"

    async def send(self, to: str, body: str) -> ProviderResult:
        message_id = str(uuid.uuid4())
        logger.info("SMS to %s: %s [id=%s]", to, body, message_id)
        return ProviderResult(success=True, provider_message_id=message_id)
