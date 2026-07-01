# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Example tool — replace with your own clinical tool implementation.

TOOL AUTHORING GUIDE
--------------------
Each tool is a Python function decorated with @tool from langchain_core.

Rules:
1. The docstring IS the tool description the LLM reads — write it carefully.
   Describe WHEN to call the tool, not just what it does.
2. All parameters must have type annotations and docstring descriptions.
3. Return a string the LLM will relay to the user (or a JSON string for
   structured data the LLM should interpret).
4. Redact PII (names, DOBs, IDs) from log lines before logging.
5. Never raise unhandled exceptions — catch and return an error string so
   the agent can recover gracefully in the voice conversation.

One file per tool. Import each tool in graph.py and add it to the tools list.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
def example_tool(query: str) -> str:
    """Answer a question or perform an action for the patient.

    Use this tool when the patient asks about <describe your use case here>.
    Do not call this tool for questions unrelated to <your domain>.

    Args:
        query: The patient's question or request, as a plain string.

    Returns:
        A concise answer string to relay to the patient, or an error message
        if the operation could not be completed.
    """
    logger.info("tool_call tool=example_tool query_length=%d", len(query))

    try:
        # ── Replace this with your actual implementation ──────────────────
        result = f"This is a placeholder response to: {query}"
        # ─────────────────────────────────────────────────────────────────

        logger.info("tool_result tool=example_tool status=ok")
        return result

    except Exception as exc:
        logger.error("tool_result tool=example_tool status=error %s", exc)
        return "I was unable to complete that request. Please try again or call the clinic directly."
