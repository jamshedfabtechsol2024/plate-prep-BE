from django import template

from app import models

register = template.Library()


@register.filter(name="current_photos")
def current_photos(value):
    pass


@register.simple_tag
def lang():
    pass
