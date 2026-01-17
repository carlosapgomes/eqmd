import asyncio
import logging

from asgiref.sync import sync_to_async
from nio import AsyncClient, RoomMessageText

from .audit import log_event
from .processor import BotMessageProcessor


logger = logging.getLogger(__name__)


class MatrixBotService:
    def __init__(self, config):
        self._config = config
        self._processor = BotMessageProcessor()
        self._client = AsyncClient(config.client_base_url, config.bot_user_id)
        self._client.access_token = config.bot_access_token

    async def run(self):
        self._client.add_event_callback(self._on_message, RoomMessageText)
        for attempt in range(3):
            try:
                await self._client.sync_forever(timeout=30000)
                return
            except Exception as exc:
                logger.exception("Matrix bot sync failed: %s", exc)
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def _on_message(self, room, event):
        if event.sender == self._config.bot_user_id:
            return

        message = getattr(event, "body", "") or ""
        try:
            result = await sync_to_async(self._processor.handle_message, thread_sensitive=True)(
                room.room_id,
                event.sender,
                message,
            )
            log_event(
                direction="inbound",
                user_id=result.user_id,
                matrix_user=event.sender,
                room_id=room.room_id,
                action=result.action,
                message=message,
                results_count=result.results_count,
                selected_patient_id=result.selected_patient_id,
            )

            for response in result.responses:
                await self._client.room_send(
                    room.room_id,
                    message_type="m.room.message",
                    content={"msgtype": "m.text", "body": response},
                )
                log_event(
                    direction="outbound",
                    user_id=result.user_id,
                    matrix_user=event.sender,
                    room_id=room.room_id,
                    action=result.action,
                    message=response,
                    results_count=result.results_count,
                    selected_patient_id=result.selected_patient_id,
                )
        except Exception as exc:
            logger.exception("Matrix bot handler error: %s", exc)
            await self._client.room_send(
                room.room_id,
                message_type="m.room.message",
                content={
                    "msgtype": "m.text",
                    "body": "Sistema temporariamente indisponivel. Tente novamente.",
                },
            )
