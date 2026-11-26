from ninja import Schema


class LoginIn(Schema):
    email: str
    password: str
    device_label: str = ""


class RefreshIn(Schema):
    refresh_token: str | None = None


class LogoutIn(Schema):
    refresh_token: str | None = None


class PasswordResetRequestIn(Schema):
    email: str


class PasswordResetConfirmIn(Schema):
    uid: str
    token: str
    new_password: str


class ActiveDivisionRef(Schema):
    season_id: int
    season_name: str
    year: int
    season_round: int
    division: int
    ladder_id: int
    is_closed: bool


class UserMeOut(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    is_staff: bool
    is_superuser: bool
    roles: list[str]
    player_id: int | None
    player_name: str | None
    active_division: ActiveDivisionRef | None


class TokenOut(Schema):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str | None = None
    user: UserMeOut


class MessageOut(Schema):
    detail: str
