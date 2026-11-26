import datetime

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from ninja import Router
from ninja.errors import HttpError

from api.auth import JWTAuth, revoke_all_user_tokens
from api.models import DevicePushToken
from api.schemas.account import (
    AccountOut,
    ChangePasswordIn,
    DeviceTokenDeleteIn,
    DeviceTokenIn,
    UpdateEmailIn,
)
from api.schemas.auth import MessageOut
from api.serializers import (
    build_active_division_ref,
    get_current_published_season,
)
from ladder.forms import EmailChangeForm
from ladder.models import LadderSubscription, League, Player

router = Router(auth=JWTAuth())


def _build_account_out(user) -> dict:
    player = Player.objects.filter(user=user).first()
    current_season = get_current_published_season()
    current_league = None
    latest_league = None

    if player:
        if current_season:
            current_league = (
                League.objects.filter(player=player, ladder__season=current_season)
                .select_related("ladder__season")
                .order_by("ladder__division")
                .first()
            )
        latest_league = (
            League.objects.filter(player=player, ladder__season__is_draft=False)
            .select_related("ladder__season")
            .order_by("-ladder__season__start_date", "ladder__division")
            .first()
        )

    today = datetime.date.today()
    subscriptions = (
        LadderSubscription.objects.filter(
            user=user,
            ladder__season__is_draft=False,
            ladder__season__end_date__gte=today,
        )
        .select_related("ladder__season")
        .order_by("-ladder__season__start_date", "ladder__division")
    )

    return {
        "email": (user.email or user.username or "").strip(),
        "player_id": player.id if player else None,
        "player_name": player.full_name(authenticated=True) if player else None,
        "current_season_name": str(current_season) if current_season else None,
        "current_division": build_active_division_ref(current_league.ladder)
        if current_league
        else None,
        "latest_division": build_active_division_ref(latest_league.ladder)
        if latest_league
        else None,
        "subscriptions": [
            {
                "ladder_id": sub.ladder_id,
                "season_name": str(sub.ladder.season),
                "year": sub.ladder.season.start_date.year,
                "season_round": sub.ladder.season.season_round,
                "division": sub.ladder.division,
                "subscribed_at": sub.subscribed_at,
            }
            for sub in subscriptions
        ],
        "active_device_count": DevicePushToken.objects.filter(
            user=user, is_active=True
        ).count(),
    }


@router.get("/", response=AccountOut)
def get_account(request):
    return _build_account_out(request.auth)


@router.patch("/email/", response=AccountOut)
def update_email(request, payload: UpdateEmailIn):
    user = request.auth
    old_email = (user.email or user.username or "").strip()
    form = EmailChangeForm(user=user, data={"email": payload.email})
    if not form.is_valid():
        errors = [err for errs in form.errors.values() for err in errs]
        raise HttpError(400, errors[0] if errors else "Invalid email address.")

    new_email = form.cleaned_data["email"]
    email_changed = old_email.lower() != new_email.lower()
    form.save()

    if email_changed:
        player = Player.objects.filter(user=user).first()
        recipients = [
            addr for addr in dict.fromkeys([old_email, new_email]) if "@" in addr
        ]
        if recipients:
            player_name = (
                f"{player.first_name} {player.last_name}".strip()
                if player
                else (user.get_full_name() or new_email)
            )
            send_mail(
                subject="Highgate Ladder - Email Address Updated",
                message=(
                    f"Hi {player_name},\n\n"
                    f"The email address for your Highgate Ladder account has been changed from {old_email} to {new_email}.\n\n"
                    f"You can now use {new_email} to log in and receive division notifications.\n\n"
                    f"If you did not request this change, please contact feedback@highgate-ladder.co.uk."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL or settings.SUBSCRIPTION_EMAIL,
                recipient_list=recipients,
                fail_silently=True,
            )

    return _build_account_out(user)


@router.post("/password/", response=MessageOut)
def change_password(request, payload: ChangePasswordIn):
    user = request.auth
    if not user.check_password(payload.old_password):
        raise HttpError(400, "Your current password was entered incorrectly.")

    try:
        validate_password(payload.new_password, user=user)
    except ValidationError as exc:
        raise HttpError(400, " ".join(exc.messages))

    user.set_password(payload.new_password)
    user.save(update_fields=["password"])
    revoke_all_user_tokens(user)

    return {"detail": "Your password has been updated successfully."}


@router.post("/devices/", response=MessageOut)
def register_device(request, payload: DeviceTokenIn):
    token = (payload.expo_push_token or "").strip()
    if not token:
        raise HttpError(400, "Push token is required.")

    DevicePushToken.objects.update_or_create(
        expo_push_token=token,
        defaults={
            "user": request.auth,
            "platform": payload.platform,
            "is_active": True,
        },
    )
    return {"detail": "Device registered for notifications."}


@router.delete("/devices/", response=MessageOut)
def unregister_device(
    request,
    payload: DeviceTokenDeleteIn | None = None,
    expo_push_token: str | None = None,
):
    raw_token = (payload.expo_push_token if payload else None) or expo_push_token
    token = (raw_token or "").strip()
    if token:
        DevicePushToken.objects.filter(
            user=request.auth, expo_push_token=token
        ).update(is_active=False)
    return {"detail": "Device unregistered."}
