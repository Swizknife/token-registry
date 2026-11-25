"""Real Twilio driver. Selected via SMS_PROVIDER=twilio with credentials set."""
import logging

import httpx

from app.config import get_settings
from app.services.sms.base import ProviderResult

logger = logging.getLogger("sms.twilio")


class TwilioSmsProvider:
    name = "twilio"

    def __init__(self) -> None:
        settings = get_settings()
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_from_number
        if not all([self.account_sid, self.auth_token, self.from_number]):
            logger.warning("Twilio provider selected but credentials are incomplete")

    async def send(self, to: str, body: str) -> ProviderResult:
        if not all([self.account_sid, self.auth_token, self.from_number]):
            return ProviderResult(success=False, error="Twilio credentials not configured")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={"To": to, "From": self.from_number, "Body": body},
                )
            if resp.status_code >= 300:
                return ProviderResult(success=False, error=f"Twilio error {resp.status_code}: {resp.text}")
            data = resp.json()
            return ProviderResult(success=True, provider_message_id=data.get("sid"))
        except httpx.HTTPError as exc:
            return ProviderResult(success=False, error=str(exc))
