from django import template

register = template.Library()


@register.simple_tag()
def print_notification(notification, user):
    return notification.print_notification(user)
