from django.contrib import admin

from .models import Comment, CommentAuthor


@admin.register(CommentAuthor)
class CommentAuthorAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "home_page")
    search_fields = ("username", "email")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("author",)
    search_fields = ("author__username", "author__email")
