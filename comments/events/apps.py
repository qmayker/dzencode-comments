from importlib import import_module

from django.apps import AppConfig


class EventsConfig(AppConfig):
    name = 'events'

    def ready(self):
        import_module("events.receivers")
