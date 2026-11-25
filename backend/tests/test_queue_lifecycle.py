import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.counter import Counter
from app.models.queue_event import QueueEvent
from app.models.token import Token, TokenStatus


async def _register(client: AsyncClient, phone="9876543210", service="Payment") -> dict:
    resp = await client.post("/api/kiosk/tokens", json={"phone_number": phone, "service_category": service})
    assert resp.status_code == 201
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_lifecycle_waiting_to_completed(
    client: AsyncClient, db: AsyncSession, seeded_counters, staff_token
):
    token = await _register(client)
    counter = seeded_counters[0]

    resp = await client.post(f"/api/counters/{counter.counter_id}/call-next", headers=_auth(staff_token))
    assert resp.status_code == 200, resp.text
    token_id = resp.json()["token_id"]

    resp = await client.post(f"/api/counters/{counter.counter_id}/serving/{token_id}", headers=_auth(staff_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "serving"

    resp = await client.post(f"/api/counters/{counter.counter_id}/complete/{token_id}", headers=_auth(staff_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    row = (await db.execute(select(Token).where(Token.token_id == token_id))).scalar_one()
    assert row.called_time is not None
    assert row.service_start_time is not None
    assert row.completion_time is not None
    assert row.called_time <= row.service_start_time <= row.completion_time

    events = (
        (await db.execute(select(QueueEvent).where(QueueEvent.token_id == token_id).order_by(QueueEvent.event_id)))
        .scalars()
        .all()
    )
    assert [e.event_type for e in events] == ["registered", "called", "serving", "completed"]

    counter_row = (await db.execute(select(Counter).where(Counter.counter_id == counter.counter_id))).scalar_one()
    assert counter_row.current_token_id is None
    assert counter_row.counter_status.value == "open"


@pytest.mark.asyncio
async def test_call_next_with_no_waiting_tokens_returns_404(client: AsyncClient, seeded_counters, staff_token):
    resp = await client.post(f"/api/counters/{seeded_counters[0].counter_id}/call-next", headers=_auth(staff_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_skip_and_requeue(client: AsyncClient, seeded_counters, staff_token):
    await _register(client)
    counter = seeded_counters[0]
    call_resp = await client.post(f"/api/counters/{counter.counter_id}/call-next", headers=_auth(staff_token))
    token_id = call_resp.json()["token_id"]

    resp = await client.post(f"/api/counters/{counter.counter_id}/skip/{token_id}", headers=_auth(staff_token))
    assert resp.json()["status"] == "skipped"

    resp = await client.post(f"/api/staff/tokens/{token_id}/requeue", headers=_auth(staff_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_mark_absent_then_requeue(client: AsyncClient, seeded_counters, staff_token):
    await _register(client)
    counter = seeded_counters[0]
    call_resp = await client.post(f"/api/counters/{counter.counter_id}/call-next", headers=_auth(staff_token))
    token_id = call_resp.json()["token_id"]

    resp = await client.post(f"/api/staff/tokens/{token_id}/absent", headers=_auth(staff_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "absent"

    resp = await client.post(f"/api/staff/tokens/{token_id}/requeue", headers=_auth(staff_token))
    assert resp.json()["status"] == "waiting"


@pytest.mark.asyncio
async def test_recall(client: AsyncClient, seeded_counters, staff_token):
    await _register(client)
    counter = seeded_counters[0]
    call_resp = await client.post(f"/api/counters/{counter.counter_id}/call-next", headers=_auth(staff_token))
    token_id = call_resp.json()["token_id"]

    resp = await client.post(f"/api/counters/{counter.counter_id}/recall/{token_id}", headers=_auth(staff_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_counter_with_assigned_service_prefers_it_then_falls_back(
    client: AsyncClient, seeded_counters, staff_token, db: AsyncSession
):
    # Counter 02 is assigned to "Payment". Register a General Enquiry token only;
    # Call Next on Counter 02 should still get it via the global fallback.
    await _register(client, service="General Enquiry")
    payment_counter = seeded_counters[1]
    resp = await client.post(f"/api/counters/{payment_counter.counter_id}/call-next", headers=_auth(staff_token))
    assert resp.status_code == 200
    assert resp.json()["service_category"] == "General Enquiry"


@pytest.mark.asyncio
async def test_staff_list_masks_phone_number(client: AsyncClient, staff_token):
    await _register(client, phone="9876543210")
    resp = await client.get("/api/staff/tokens", headers=_auth(staff_token))
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["phone_masked"].endswith("3210")
    assert "9876" not in rows[0]["phone_masked"]


@pytest.mark.asyncio
async def test_staff_cannot_access_unmasked_detail(client: AsyncClient, staff_token):
    token = await _register(client)
    resp = await client.get(f"/api/staff/tokens/{token['token_id']}", headers=_auth(staff_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_unmasked_detail(client: AsyncClient, admin_token):
    token = await _register(client)
    resp = await client.get(f"/api/staff/tokens/{token['token_id']}", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["phone_number"].endswith("3210")


@pytest.mark.asyncio
async def test_public_display_has_no_pii(client: AsyncClient, seeded_counters, staff_token):
    await _register(client, phone="9876543210")
    resp = await client.get("/api/public/display")
    assert resp.status_code == 200
    body = resp.json()
    raw = resp.text
    assert "9876543210" not in raw
    assert "phone" not in raw.lower()
    assert "customer" not in raw.lower()
    assert body["upcoming"] == ["A001"]
