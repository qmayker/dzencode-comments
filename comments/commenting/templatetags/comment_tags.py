from django import template
from django.utils.safestring import mark_safe

from commenting.services.models.comment.text import CommentTextSanitizer

register = template.Library()
sanitizer = CommentTextSanitizer()


@register.filter
def sanitize_comment_html(value: str):
    return mark_safe(sanitizer.clean(value).text)
