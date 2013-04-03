from django import template

register = template.Library()


@register.filter(name='getkey')
def getkey(value, arg):
    try:
        return value[arg]
    except:
        return
