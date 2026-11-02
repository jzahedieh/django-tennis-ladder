import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver

from ladder.models import LadderSubscription, League


@receiver(post_save, sender=League)
def auto_subscribe_on_league_create(sender, instance: League, created, **kwargs):
    if not created:
        return
    player = instance.player
    # only if the player has a linked user
    if getattr(player, "user_id", None):
        LadderSubscription.objects.get_or_create(
            ladder=instance.ladder,
            user=player.user,
            defaults={'subscribed_at': datetime.date.today()}
        )
