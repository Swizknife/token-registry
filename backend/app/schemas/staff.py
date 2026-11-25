from pydantic import BaseModel


class OverviewResponse(BaseModel):
    total_registered_today: int
    currently_waiting: int
    being_served: int
    completed_today: int
    active_counters: int
    counters_now_serving: dict[str, str | None]
