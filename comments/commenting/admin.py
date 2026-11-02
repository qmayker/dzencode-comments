from django.contrib import admin

from commenting.services.models.author.create import CommentAuthorService
from commenting.services.models.comment.create import (
    CommentReplyService,
    CommentService,
)

from .models import Comment, CommentAuthor


@admin.register(CommentAuthor)
class CommentAuthorAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "home_page")
    search_fields = ("username", "email")

    def save_model(self, request, obj, form, change):
        service = CommentAuthorService(obj)
        service.save()


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author",)
    search_fields = ("author__username", "author__email")

    def save_model(self, request, obj: Comment, form, change):
        if obj.related_comment_id is None:
            ServiceType = CommentService
        else:
            ServiceType = CommentReplyService
        service = ServiceType(obj)
        service.save()
