import datetime
from typing import Literal

from ninja import Schema

from api.schemas.auth import ActiveDivisionRef


class SubscriptionRef(Schema):
    ladder_id: int
    season_name: str
    year: int
    season_round: int
    division: int
    subscribed_at: datetime.date


class AccountOut(Schema):
    email: str
    player_id: int | None
    player_name: str | None
    current_season_name: str | None
    current_division: ActiveDivisionRef | None
    latest_division: ActiveDivisionRef | None
    subscriptions: list[SubscriptionRef]
    active_device_count: int


class UpdateEmailIn(Schema):
    email: str


class ChangePasswordIn(Schema):
    old_password: str
    new_password: str


class DeviceTokenIn(Schema):
    expo_push_token: str
    platform: Literal["ios", "android", "web"]


class DeviceTokenDeleteIn(Schema):
    expo_push_token: str
