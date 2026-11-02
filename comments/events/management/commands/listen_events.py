import redis
from django.conf import settings
from django.core.management.base import BaseCommand

from events.listener import RedisEventListener
from events.receivers import receiver_registry


class Command(BaseCommand):
    help = "Listen for JSON events stored in a Redis list."

    def handle(self, *args, **options):
        redis_client = redis.Redis.from_url(settings.EVENTS_REDIS_URL)

        listener = RedisEventListener(
            redis_client=redis_client,
            list_name=settings.EVENTS_REDIS_KEY,
            registry=receiver_registry,
        )
        try:
            self.stdout.write("started listening")
            listener.listen()
        finally:
            self.stdout.write("stopped listening")
            redis_client.close()
