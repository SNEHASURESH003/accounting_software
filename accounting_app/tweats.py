from django import template

register = template.Library()

@register.filter
def tweats(field):
    return field.as_widget(attrs={'class': 'form-control'})
