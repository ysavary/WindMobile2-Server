from django.template import Library

register = Library()


@register.filter(is_safe=True)
def value(dict, key):
    return dict[key]
