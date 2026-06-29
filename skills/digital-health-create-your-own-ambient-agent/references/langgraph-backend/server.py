# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""FastAPI server — OpenAI-compatible /v1/chat/completions endpoint.

The Nemotron Voice Agent calls this endpoint instead of a raw LLM NIM.
Set NVIDIA_LLM_URL=http://agent-backend:${AGENT_PORT}/v1 in the voice agent's
environment to route requests through this server.

DO NOT rewrite this file from scratch. The streaming and SSE logic is
load-bearing; the Nemotron Voice Agent relies on exact SSE framing.
Extend by adding new routes or middleware below the existing routes.
"""

import json
import logging
import os
import time
import traceback
import uuid
from typing import AsyncIterator, List, Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from pydantic import BaseModel

load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5s [%(name)s] %(message)s",
)
logger = logging.getLogger("agent")

from agent.graph import SYSTEM_PROMPT, get_graph  # noqa: E402

app = FastAPI(title="Ambient Healthcare Agent", version="1.0.0")
AGENT_MODEL_NAME = os.getenv("AGENT_MODEL_NAME", "ambient-healthcare-agent")
DEFAULT_LLM_MODEL = "nvidia/nemotron-3-super-120b-a12b"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas (OpenAI-compatible)
# ---------------------------------------------------------------------------


class MessageParam(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = AGENT_MODEL_NAME
    messages: List[MessageParam]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------


def _prepare_messages(incoming: List[MessageParam]) -> list:
    """Strip voice-agent system prompts and inject the agent's own prompt."""
    non_system = [m for m in incoming if m.role != "system"]

    lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in non_system:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    # Ensure at least one HumanMessage so the agent runs
    if not any(isinstance(msg, HumanMessage) for msg in lc_messages):
        lc_messages.append(HumanMessage(content="Please begin."))

    return lc_messages


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------


def _sse_chunk(content: str, request_id: str, model: str) -> str:
    data = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(data)}\n\n"


def _sse_stop(request_id: str, model: str) -> str:
    data = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    return f"data: {json.dumps(data)}\n\n"


def _mock_content(messages: list) -> str:
    """Deterministic local smoke-test response; never enabled by default."""
    last_user = next(
        (m.content for m in reversed(messages) if isinstance(m, HumanMessage)),
        "Hello",
    )
    return f"Mock agent response received: {last_user[:120]}"


async def _stream_agent(messages: list, request_id: str, model: str) -> AsyncIterator[str]:
    """Run the LangGraph agent and yield SSE-formatted token chunks."""
    if os.getenv("LLM_MOCK_MODE", "false").lower() == "true":
        yield _sse_chunk(_mock_content(messages), request_id, model)
        yield _sse_stop(request_id, model)
        yield "data: [DONE]\n\n"
        return

    graph = get_graph()
    try:
        async for chunk, metadata in graph.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            if metadata.get("langgraph_node") != "agent":
                continue
            if not isinstance(chunk, AIMessageChunk):
                continue
            if getattr(chunk, "tool_call_chunks", None):
                continue  # tool-call chunks are not spoken text
            if chunk.content:
                yield _sse_chunk(str(chunk.content), request_id, model)
    except Exception:
        tb = traceback.format_exc()
        logger.error("stream_error\n%s", tb)
        yield _sse_chunk(
            "I'm sorry, I encountered an error. Please try again.",
            request_id,
            model,
        )

    yield _sse_stop(request_id, model)
    yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    logger.info(
        "request_received messages=%d stream=%s",
        len(request.messages),
        request.stream,
    )

    messages = _prepare_messages(request.messages)

    if request.stream:
        return StreamingResponse(
            _stream_agent(messages, request_id, request.model),
            media_type="text/event-stream",
            headers={"X-Request-ID": request_id},
        )

    try:
        if os.getenv("LLM_MOCK_MODE", "false").lower() == "true":
            final_content = _mock_content(messages)
        else:
            graph = get_graph()
            result = await graph.ainvoke({"messages": messages})
            final_content = str(result["messages"][-1].content)
        logger.info("llm_response preview=%.500s", final_content)
    except Exception:
        tb = traceback.format_exc()
        logger.error("unhandled_exception\n%s", tb)
        return JSONResponse(status_code=500, content={"error": "Internal server error"})

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": final_content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [{"id": AGENT_MODEL_NAME, "object": "model", "created": 0, "owned_by": "custom"}],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/config")
async def debug_config():
    """Return non-secret effective runtime config for deployment troubleshooting."""
    return {
        "agent_model_name": AGENT_MODEL_NAME,
        "agent_port": os.getenv("AGENT_PORT", "8000"),
        "llm_model": os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        "llm_base_url": os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        "llm_mock_mode": os.getenv("LLM_MOCK_MODE", "false").lower() == "true",
        "guardrails_enabled": os.getenv("GUARDRAILS_ENABLED", "false").lower() == "true",
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    port = int(os.getenv("AGENT_PORT", "8000"))
    uvicorn.run("agent.server:app", host="0.0.0.0", port=port, reload=False)
