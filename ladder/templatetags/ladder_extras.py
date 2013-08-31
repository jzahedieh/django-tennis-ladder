from django import template

register = template.Library()


@register.filter(name='getkey')
def getkey(value, arg):
    try:
        return value[arg]
    except:
        return

@register.filter(name='gettotal')
def gettotal(value, arg):
    total = 0
    try:
        for result in value[arg]:
            if result.result == 9:
                total = total + result.result + 3
            else:
                total = total + result.result + 1
        return total
    except KeyError:
        return total

@register.filter(name='unplayed')
def unplayed(value, arg):
    not_played = []
    try:
        not_played = [player for player in value if player.id != arg]

        return not_played
    except:
        return