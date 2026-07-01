# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""LangGraph agent graph — ReAct pattern reference implementation.

This file demonstrates the ReAct graph pattern using create_react_agent.
Use it as a starting point if the developer chose ReAct in Phase 1 (d).
For other graph types (custom conditional graph, sequential workflow), use
this file as a structural reference for env var loading, the singleton
pattern, and the streaming filter — but replace create_react_agent with
a StateGraph implementation appropriate to the chosen pattern.

CUSTOMIZATION GUIDE (ReAct pattern)
------------------------------------
1. Replace SYSTEM_PROMPT with a prompt suited to your clinical use case.
2. Replace the `tools` list with your own tool functions from agent/tools/.
3. LLM parameters are read from env vars at startup; no code changes needed
   to switch models or enable/disable thinking mode.
4. LLM_BASE_URL defaults to the NVIDIA public AI Endpoint — no local GPU
   required. Set it to a local NIM URL (e.g. http://localhost:8000/v1) to
   route requests to a self-hosted NIM instead.
"""

import logging
import os

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.prebuilt import create_react_agent

# ── Replace these imports with your own tools ──────────────────────────────
from agent.tools.example_tool import example_tool

# ── Add any additional tools here ──────────────────────────────────────────
# from agent.tools.appointments import book_appointment
# from agent.tools.prescriptions import request_refill

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────
# Write a prompt specific to your clinical use case. Keep it concise —
# this is a voice interface, so responses should be 1–3 sentences.
SYSTEM_PROMPT = """You are a friendly healthcare voice assistant.
Your job is to help patients with their requests through natural conversation.

Guidelines:
- Be warm, concise, and patient.
- Keep responses to 1–3 sentences — this is a voice interface.
- Use tools whenever they can help fulfil the patient's request.
- If you cannot help, say so clearly and suggest the patient call the clinic."""

_graph = None


def get_graph():
    """Return the singleton LangGraph ReAct agent, building it on first call."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph


def _build_graph():
    enable_thinking_str = os.getenv("LLM_ENABLE_THINKING", "false").lower()
    enable_thinking = enable_thinking_str == "true"

    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    if enable_thinking and max_tokens < 8192:
        max_tokens = 8192

    model_kwargs: dict = {}
    if enable_thinking:
        # Only pass this parameter to models that support it (e.g. Nemotron Super).
        # Passing it to unsupported models causes an API error.
        model_kwargs["extra_body"] = {
            "chat_template_kwargs": {"enable_thinking": True}
        }

    # ChatNVIDIA defaults to the public NVIDIA AI Endpoint when LLM_BASE_URL
    # is not set. Point LLM_BASE_URL at a local NIM to use a self-hosted model.
    llm = ChatNVIDIA(
        model=os.getenv("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
        base_url=os.getenv("LLM_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NVIDIA_API_KEY", ""),
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
        max_tokens=max_tokens,
        model_kwargs=model_kwargs if model_kwargs else {},
    )

    # ── Replace with your own tool list ────────────────────────────────────
    tools = [example_tool]

    graph = create_react_agent(llm, tools=tools)
    logger.info(
        "graph_built model=%s thinking=%s max_tokens=%d tools=%s",
        os.getenv("LLM_MODEL"),
        enable_thinking,
        max_tokens,
        [t.name for t in tools],
    )
    return graph
