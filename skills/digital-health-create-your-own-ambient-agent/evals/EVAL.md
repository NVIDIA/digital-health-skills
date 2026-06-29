# Evaluation Notes

This eval suite is P0 smoke coverage for the `digital-health-create-your-own-ambient-agent`
skill. Keep the cases small enough for the first publication gate and expand
after the initial NVCARPS path is stable.

## Intent

- Verify the skill triggers for ambient healthcare voice-agent creation,
  Nemotron Voice Agent + FastAPI + LangGraph architecture, and spec-driven
  scaffold requests.
- Verify the skill stays silent for general healthcare education and standalone
  LangGraph prompts outside the full ambient-agent architecture.
- Verify first-step behavior: the agent must start with prerequisite reference
  confirmation and preserve explicit approval gates before cloning, installing,
  writing specs, or generating code.

## Run Locally

Schema and static validation:

```bash
nv-base validate <path-to-skill-directory> --external --no-llm --no-dedup -r cli
```

Live Tier 3 evaluation, once `astra-skill-eval` is available:

```bash
export PATH="$HOME/.local/share/uv/tools/nv-base/bin:$PATH"
export OTEL_SDK_DISABLED=true
nv-base agent-eval <path-to-skill-directory> \
  -a claude-code,codex \
  --skip-baseline \
  --no-llm-judge \
  -k 1 \
  --outer-timeout 3600
```

For the publication benchmark run, remove `--skip-baseline` and include both
with-skill and without-skill results for Claude Code and Codex.

## Review Checklist

- Positive cases cover trigger, bootstrap, specification, and architecture
  recognition.
- Negative cases cover common false positives: general healthcare content and
  standalone LangGraph examples.
- Cases do not require live NVIDIA APIs, Docker, microphone access, or cloning
  repositories to pass.
- `expected_skill: null` is used only on negative trigger cases.
