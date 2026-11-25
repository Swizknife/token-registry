"""SMS provider abstraction. Swap drivers via SMS_PROVIDER env var."""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class ProviderResult:
    success: bool
    provider_message_id: str | None = None
    error: str | None = None


class SmsProvider(Protocol):
    name: str

    async def send(self, to: str, body: str) -> ProviderResult: ...
