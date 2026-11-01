import json
import time
import pika
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from audit.models import AuditEvent, AuditSeverity, IngestedMessageId

class Command(BaseCommand):
    help = "Asynchronously consumes CloudEvents from RabbitMQ topic exchange to log immutable audit records."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process available messages and exit")

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

        # Declare dedicated audit queue
        queue_name = "trustgrid.audit.events"
        channel.queue_declare(queue=queue_name, durable=True)

        # Bind to all trustgrid events
        channel.queue_bind(exchange="trustgrid.events", queue=queue_name, routing_key="#")

        run_once = options.get("once", False)
        self.stdout.write(self.style.SUCCESS("Listening for platform events to audit..."))

        def process_message(ch, method, properties, body):
            try:
                payload = json.loads(body.decode("utf-8"))
                message_id = payload.get("id") or properties.message_id or str(time.time())
                event_type = payload.get("type", "unknown.event")
                tenant_id = payload.get("tenantid")

                if not tenant_id:
                    self.stdout.write(self.style.WARNING(f"Skipping event {message_id}: no tenantid"))
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                # Exactly-once idempotency check
                with transaction.atomic():
                    if IngestedMessageId.objects.filter(message_id=message_id).exists():
                        self.stdout.write(self.style.NOTICE(f"Duplicate message {message_id} ignored."))
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    IngestedMessageId.objects.create(message_id=message_id, event_type=event_type)

                    data = payload.get("data", {})
                    action = event_type
                    resource_type = action.split(".")[0] if "." in action else "general"
                    resource_id = data.get("id") or data.get("assessment_id") or data.get("vendor_id") or message_id

                    # Create immutable audit record
                    AuditEvent.objects.create(
                        organization_id=tenant_id,
                        actor_id=data.get("submitted_by") or data.get("actor_id") or "system",
                        actor_email=data.get("actor_email") or "",
                        action=action,
                        resource_type=resource_type,
                        resource_id=str(resource_id),
                        severity=AuditSeverity.INFO,
                        description=f"Automated audit entry for {event_type}",
                        metadata=data,
                        correlation_id=payload.get("correlationid", ""),
                    )

                self.stdout.write(self.style.SUCCESS(f"Audited event {message_id} ({event_type}) for tenant {tenant_id}"))
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Error processing message: {exc}"))
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        if run_once:
            while True:
                method_frame, header_frame, body = channel.basic_get(queue=queue_name, auto_ack=False)
                if method_frame:
                    process_message(channel, method_frame, header_frame, body)
                else:
                    break
            connection.close()
        else:
            channel.basic_qos(prefetch_count=10)
            channel.basic_consume(queue=queue_name, on_message_callback=process_message)
            try:
                channel.start_consuming()
            except KeyboardInterrupt:
                channel.stop_consuming()
            finally:
                connection.close()