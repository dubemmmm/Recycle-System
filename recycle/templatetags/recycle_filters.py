from django import template

register = template.Library()

@register.filter
def split(value, delimiter):
    """Split a string by the given delimiter and return a list of strings."""
    if not value:
        return []
    return value.split(delimiter)

@register.filter
def trim(value):
    """Remove leading and trailing whitespace from a string."""
    if not value:
        return ""
    return value.strip()