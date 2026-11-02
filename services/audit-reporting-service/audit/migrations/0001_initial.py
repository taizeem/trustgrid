import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='IngestedMessageId',
            fields=[
                ('message_id', models.CharField(max_length=128, primary_key=True, serialize=False)),
                ('event_type', models.CharField(max_length=120)),
                ('ingested_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'ingested_messages',
            },
        ),
        migrations.CreateModel(
            name='AuditEvent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('organization_id', models.UUIDField(db_index=True)),
                ('actor_id', models.CharField(blank=True, db_index=True, default='system', max_length=128)),
                ('actor_email', models.EmailField(blank=True, default='', max_length=254)),
                ('action', models.CharField(db_index=True, max_length=120)),
                ('resource_type', models.CharField(db_index=True, max_length=64)),
                ('resource_id', models.CharField(db_index=True, max_length=128)),
                ('severity', models.CharField(choices=[('INFO', 'Information'), ('WARNING', 'Warning'), ('CRITICAL', 'Critical')], db_index=True, default='INFO', max_length=16)),
                ('description', models.TextField(blank=True, default='')),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, default='', max_length=256)),
                ('correlation_id', models.CharField(blank=True, db_index=True, default='', max_length=128)),
                ('checksum', models.CharField(blank=True, editable=False, max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'db_table': 'audit_events',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['organization_id', '-created_at'], name='idx_audit_org_time'),
                    models.Index(fields=['organization_id', 'action', '-created_at'], name='idx_audit_org_act_time'),
                    models.Index(fields=['organization_id', 'resource_type', 'resource_id'], name='idx_audit_org_resource'),
                ],
            },
        ),
    ]