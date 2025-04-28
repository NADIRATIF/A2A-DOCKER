from typing import AsyncIterable, Callable
import asyncio
import google_a2a
from google_a2a.common.server.task_manager import InMemoryTaskManager
from google_a2a.common.types import (
    Artifact,
    JSONRPCResponse,
    Message,
    SendTaskRequest,
    SendTaskResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Task,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

class MyAgentTaskManager(InMemoryTaskManager):
    def __init__(self, query_ollama_function: Callable[[str], str | None]):
        super().__init__()
        self._query_ollama = query_ollama_function

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        await self.upsert_task(request.params)
        task_id = request.params.id
        user_query = request.params.message.parts[0].text
        llm_response = self._query_ollama(user_query)
        if llm_response:
            response_text = f"Ollama says: {llm_response}"
        else:
            response_text = "Failed to get response from Ollama."
        task = await self._update_task(
            task_id=task_id,
            task_state=TaskState.COMPLETED,
            response_text=response_text
        )
        return SendTaskResponse(id=request.id, result=task)

    async def on_send_task_subscribe(
        self,
        request: SendTaskStreamingRequest
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        task_id = request.params.id
        await self.upsert_task(request.params)
        sse_event_queue = await self.setup_sse_consumer(task_id=task_id)
        asyncio.create_task(self._handle_streaming(request))
        return self.dequeue_events_for_sse(
            request_id=request.id,
            task_id=task_id,
            sse_event_queue=sse_event_queue,
        )

    async def _handle_streaming(self, request: SendTaskStreamingRequest):
        task_id = request.params.id
        user_query = request.params.message.parts[0].text
        llm_response = self._query_ollama(user_query)
        if llm_response:
            parts = [{"type": "text", "text": f"Ollama streaming: {llm_response}"}]
            message = Message(role="agent", parts=parts)
            task_status = TaskStatus(state=TaskState.COMPLETED, message=message)
            task_update_event = TaskStatusUpdateEvent(
                id=task_id, status=task_status, final=True
            )
            await self.enqueue_events_for_sse(task_id, task_update_event)
        else:
            error_message = Message(role="agent", parts=[{"type": "text", "text": "Ollama streaming failed."}])
            task_status = TaskStatus(state=TaskState.ERROR, message=error_message)
            task_update_event = TaskStatusUpdateEvent(
                id=task_id, status=task_status, final=True
            )
            await self.enqueue_events_for_sse(task_id, task_update_event)

    async def _update_task(
        self,
        task_id: str,
        task_state: TaskState,
        response_text: str,
    ) -> Task:
        task = self.tasks[task_id]
        agent_response_parts = [{"type": "text", "text": response_text}]
        task.status = TaskStatus(
            state=task_state, message=Message(role="agent", parts=agent_response_parts)
        )
        task.artifacts = [Artifact(parts=agent_response_parts)]
        return task
