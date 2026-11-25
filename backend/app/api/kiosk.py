import phonenumbers
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.schemas.token import SERVICE_CATEGORIES, TokenCreateRequest, TokenCreateResponse
from app.services.realtime import broadcaster
from app.services.tokens import register_token

router = APIRouter(prefix="/api", tags=["kiosk"])
settings = get_settings()


@router.get("/services")
async def list_services() -> list[str]:
    return SERVICE_CATEGORIES


def _normalize_phone(raw: str) -> str:
    try:
        parsed = phonenumbers.parse(raw, "IN")
    except phonenumbers.NumberParseException as exc:
        raise HTTPException(status_code=422, detail="Invalid phone number") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise HTTPException(status_code=422, detail="Invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@router.post("/kiosk/tokens", response_model=TokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_token(payload: TokenCreateRequest, db: AsyncSession = Depends(get_db)) -> TokenCreateResponse:
    phone = _normalize_phone(payload.phone_number)
    token = await register_token(db, phone_number=phone, service_category=payload.service_category)

    await broadcaster.broadcast(
        "token.created",
        {
            "token_id": token.token_id,
            "token_number": token.token_number,
            "service_category": token.service_category,
        },
    )
    await broadcaster.broadcast("display.refresh", {})

    return TokenCreateResponse(
        token_id=token.token_id,
        token_number=token.token_number,
        service_category=token.service_category,
        status=token.status.value,
        registration_time=token.registration_time,
        estimated_wait_time=token.estimated_wait_time,
        queue_url=settings.public_queue_url,
    )
