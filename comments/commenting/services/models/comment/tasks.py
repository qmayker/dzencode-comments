from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.console import EmailBackend

logger = get_task_logger(__name__)


@shared_task
def send_reply_email(reply_id: int) -> int:
    from commenting.models import Comment

    reply = (
        Comment.objects.select_related(
            "author",
            "target_comment__author",
        )
        .filter(pk=reply_id)
        .first()
    )
    if reply is None:
        logger.error(f"Couldnt find comment to reply with id {reply_id}")
        return 0
    target = reply.target_comment
    if target is None or target.author_id == reply.author_id:
        return 0

    result = send_mail(
        subject="New reply to your comment",
        message=(
            f"Hi {target.author.username},\n\n"
            f"{reply.author.username} replied to your comment:\n\n"
            f"{reply.text}\n\n"
            f"Your comment:\n{target.text}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[target.author.email],
        connection=EmailBackend(),
        fail_silently=False,
    )
    return result
