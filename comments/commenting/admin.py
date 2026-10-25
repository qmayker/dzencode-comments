from django.contrib import admin

from commenting.services.models.comment.create import CommentService

from .models import Comment, CommentAuthor


@admin.register(CommentAuthor)
class CommentAuthorAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "home_page")
    search_fields = ("username", "email")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author",)
    search_fields = ("author__username", "author__email")

    def save_model(self, request, obj, form, change):
        service = CommentService(obj)
        service.save()
