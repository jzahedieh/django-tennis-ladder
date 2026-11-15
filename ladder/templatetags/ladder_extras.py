from django import template

register = template.Library()


@register.simple_tag
def get_player_name(player, user):
    return player.full_name(authenticated=user.is_authenticated)
