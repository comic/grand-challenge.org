import random

from django import template

register = template.Library()


register.simple_tag(lambda b, e: random.randint(b, e), name="randint")
