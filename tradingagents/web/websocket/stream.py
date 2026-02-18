"""WebSocket handler for streaming task progress to the browser."""

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


async def websocket_stream_handler(
    websocket: WebSocket,
    task_id: str,
    task_manager: Any,
) -> None:
    """Handle a WebSocket connection for streaming task progress.

    The client connects to /ws/stream/{task_id} and receives JSON messages
    with progress updates until the task completes or the connection closes.

    Args:
        websocket: The FastAPI WebSocket connection.
        task_id: ID of the task to stream updates for.
        task_manager: TaskManager instance for status lookups.
    """
    await websocket.accept()
    logger.info("WebSocket connected for task: %s", task_id)

    update_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_update(_task_id: str, status: Dict[str, Any]) -> None:
        """Thread-safe callback: push update into async queue."""
        loop.call_soon_threadsafe(update_queue.put_nowait, status)

    task_manager.subscribe(task_id, on_update)

    try:
        status = task_manager.get_status(task_id)
        if status is None:
            await websocket.send_json({
                "type": "error",
                "task_id": task_id,
                "message": f"Task '{task_id}' not found",
            })
            await websocket.close()
            return

        await websocket.send_json({
            "type": "progress",
            "task_id": task_id,
            **status,
        })

        while True:
            try:
                update = await asyncio.wait_for(
                    update_queue.get(), timeout=30.0
                )
                await websocket.send_json({
                    "type": "progress",
                    "task_id": task_id,
                    **update,
                })

                if update.get("status") in ("completed", "failed", "cancelled"):
                    await websocket.send_json({
                        "type": "complete",
                        "task_id": task_id,
                        **update,
                    })
                    break

            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "ping",
                    "task_id": task_id,
                })

            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(), timeout=0.01
                )
                msg = json.loads(raw)
                if msg.get("type") == "cancel":
                    task_manager.cancel(task_id)
                    await websocket.send_json({
                        "type": "progress",
                        "task_id": task_id,
                        "message": "Cancellation requested",
                    })
            except (asyncio.TimeoutError, json.JSONDecodeError):
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for task: %s", task_id)
    except Exception as exc:
        logger.error("WebSocket error for task %s: %s", task_id, exc)
    finally:
        task_manager.unsubscribe(task_id, on_update)
        try:
            await websocket.close()
        except Exception:
            pass
