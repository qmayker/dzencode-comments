from django.db import models

from .validators import UserNameValidator


class CommentAuthor(models.Model):
    username = models.CharField(
        max_length=100, validators=[UserNameValidator()], unique=True
    )
    email = models.EmailField(unique=True)
    home_page = models.URLField(null=True, blank=True)

    def __str__(self):
        return f"{self.username}"


class Comment(models.Model):
    author = models.ForeignKey(
        CommentAuthor, on_delete=models.CASCADE, related_name="comments"
    )
    related_comment = models.ForeignKey(
        "self", null=True, blank=True, related_name="replies", on_delete=models.CASCADE
    )
    text = models.TextField(max_length=2000)

    def __str__(self):
        return f"{self.author.username} {self.text[:25]}"
