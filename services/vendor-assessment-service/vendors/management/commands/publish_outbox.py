import json
import time
import pika
from django.conf import settings
from django.utils import timezone
from django.core.management.base import BaseCommand
from vendors.models import OutboxEvent, OutboxStatus

class Command(BaseCommand):
    help = "Relays pending outbox events to the RabbitMQ topic exchange"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")

    def handle(self, *args, **options):
        rabbitmq_host = getattr(settings, "RABBITMQ_HOST", "rabbitmq")
        rabbitmq_port = int(getattr(settings, "RABBITMQ_PORT", 5672))
        rabbitmq_user = getattr(settings, "RABBITMQ_USER", "trustgrid_mq")
        rabbitmq_pass = getattr(settings, "RABBITMQ_PASS", "trustgrid_mq_pass_dev")
        rabbitmq_vhost = getattr(settings, "RABBITMQ_VHOST", "trustgrid_vhost")

        credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
        parameters = pika.ConnectionParameters(
            host=rabbitmq_host,
            port=rabbitmq_port,
            virtual_host=rabbitmq_vhost,
            credentials=credentials,
            heartbeat=60,
        )

        self.stdout.write(self.style.SUCCESS(f"Connecting to RabbitMQ at {rabbitmq_host}:{rabbitmq_port}..."))
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare durable exchange
        channel.exchange_declare(exchange="trustgrid.events", exchange_type="topic", durable=True)
        # Enable publisher confirms
        channel.confirm_delivery()

        run_once = options.get("once", False)

        try:
            while True:
                events = OutboxEvent.objects.filter(status=OutboxStatus.PENDING).order_by("created_at")[:50]
                if not events.exists():
                    if run_once:
                        break
                    time.sleep(2)
                    continue

                for event in events:
                    try:
                        channel.basic_publish(
                            exchange="trustgrid.events",
                            routing_key=event.routing_key,
                            body=json.dumps(event.payload),
                            properties=pika.BasicProperties(
                                delivery_mode=2,  # Persistent message on disk
                                content_type="application/json",
                                message_id=str(event.id),
                            ),
                            mandatory=False,
                        )
                        event.status = OutboxStatus.PUBLISHED
                        event.published_at = timezone.now()
                        event.save(update_fields=["status", "published_at"])
                        self.stdout.write(self.style.SUCCESS(f"Published event {event.id} ({event.routing_key})"))
                    except Exception as exc:
                        self.stdout.write(self.style.ERROR(f"Failed to publish event {event.id}: {exc}"))
                        event.status = OutboxStatus.FAILED
                        event.retry_count += 1
                        event.save(update_fields=["status", "retry_count"])

                if run_once:
                    break
        finally:
            connection.close()
