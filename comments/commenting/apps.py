from django.apps import AppConfig


class CommentingConfig(AppConfig):
    name = 'commenting'

    def ready(self):
        from . import signals
