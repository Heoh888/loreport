import json
import uuid

import aio_pika

from loreport_core.types import LoreportCommand, SyncJobPayload
from loreport_server.config import Settings, get_settings


async def publish_sync_job(
    settings: Settings,
    *,
    job_id: uuid.UUID,
    command: LoreportCommand,
    repo_path: str,
    language: str | None = None,
) -> None:
    payload = SyncJobPayload(
        id=str(job_id),
        command=command,
        repo_path=repo_path,
        language=language,
    )
    if get_settings().is_standalone:
        from loreport_server.queue.local import enqueue

        await enqueue(payload)
        return

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            settings.sync_exchange, aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await channel.declare_queue(settings.sync_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.sync_routing_key)
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload.model_dump()).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=settings.sync_routing_key,
        )
