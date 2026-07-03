import asyncio
import json
import logging

import aio_pika

from loreport_core.types import SyncJobPayload
from loreport_server.config import get_settings
from loreport_server.db.session import init_db
from loreport_server.worker.jobs import process_job

logger = logging.getLogger(__name__)


async def consume() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    await init_db()

    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        exchange = await channel.declare_exchange(
            settings.sync_exchange, aio_pika.ExchangeType.DIRECT, durable=True
        )
        queue = await channel.declare_queue(settings.sync_queue, durable=True)
        await queue.bind(exchange, routing_key=settings.sync_routing_key)

        logger.info("Worker listening on queue %s", settings.sync_queue)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process(requeue=True):
                    raw = json.loads(message.body.decode())
                    payload = SyncJobPayload.model_validate(raw)
                    logger.info("Processing job %s command=%s", payload.id, payload.command)
                    await process_job(payload)


def main() -> None:
    asyncio.run(consume())


if __name__ == "__main__":
    main()
