# Validation and Handoff

Use this reference for Phase 5. It covers static checks, test suites, Docker
Compose validation, optional guardrails validation, the final checklist, and the
handoff response.

## Contents

- Phase 5: Validate
- Static and configuration checks
- Generated runnable skill adequacy audit
- Unit, integration, and end-to-end tests
- Optional guardrails validation
- Final checklist
- Final handoff to developer

## Phase 5: Validate

Validation runs at three levels. All three must pass before declaring the
implementation complete. Guardrails validation is an additional requirement if
Phase 2(f) was enabled.

---

### Static and configuration checks

Run these before any live LLM call or Docker startup. They catch placeholder,
import, port-contract, and compose-file mistakes without changing the launch
experience.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m compileall agent tests scripts
python -c "from agent.server import app; print(app.title)"
docker compose config >/tmp/<agent-name>-compose.yml
rg -n "TODO|FIXME|REPLACE_ME|<agent-name>|<tool_name>|placeholder" agent tests scripts README.md docs .agents docker-compose.yml Dockerfile .env.example
```

If guardrails are enabled, run this in the same virtual environment immediately
after `pip install -r requirements.txt` and before handoff:

```bash
python - <<'PY'
import os
from nemoguardrails import RailsConfig

RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
print("guardrails config load PASS")
PY
```

This check validates the generated config against whichever `nemoguardrails`
version was actually installed from `requirements.txt`. Do not pin the package
only to satisfy a stale config expression; fix the generated config or record the
dependency/config failure as a blocker.

The placeholder scan should return no hits except intentional documentation
examples that have already been replaced with the concrete generated agent name.
If `rg` returns a real placeholder, fix it before continuing.

**Checklist**
- [ ] `python -m compileall agent tests scripts` passes
- [ ] `from agent.server import app` imports without building a live LLM request
- [ ] If guardrails enabled: `RailsConfig.from_path(...)` loads
  `config/guardrails/` using the installed `nemoguardrails` version
- [ ] If guardrails enabled with tools: `python -m pytest tests/test_graph.py -v`
  includes and passes the ReAct/Guardrails `bind_tools()` regression
- [ ] `docker compose config` renders successfully
- [ ] No unresolved placeholders remain in source, docs, compose, or env examples
- [ ] `.env.example` contains `AGENT_MODEL_NAME`, `AGENT_PORT`,
  `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`, and `LLM_MOCK_MODE=false`
- [ ] Docker Compose uses `NVIDIA_LLM_MODEL=${AGENT_MODEL_NAME:-<agent-name>}`
  for `nemotron-voice-agent`

---

### Generated runnable skill adequacy audit

Before validating the Docker stack, audit the generated
`.agents/skills/<agent-name>/SKILL.md` as a first-class artifact. Passing tests
is not enough if the generated skill is too thin for Claude Code, Codex, or
another coding agent to operate the repo later.

Run a structural audit:

```bash
python - <<'PY'
from pathlib import Path
import re

agent_name = "<agent-name>"
path = Path(".agents/skills") / agent_name / "SKILL.md"
text = path.read_text(encoding="utf-8")

assert path.exists(), f"missing {path}"
assert text.startswith("---\n"), "missing YAML frontmatter"
frontmatter = text.split("---", 2)[1]
assert re.search(rf"^name:\s*{re.escape(agent_name)}\s*$", frontmatter, re.M), "frontmatter name must match directory"
assert re.search(r"^description:\s*", frontmatter, re.M), "frontmatter description is required"

required_sections = [
    "Repo Layout",
    "Getting Started",
    "Prerequisites",
    "Start",
    "Stop",
    "Status",
    "Logs",
    "Run Tests",
    "Smoke Test",
    "Configuration",
    "Add a New Tool",
]
missing = [section for section in required_sections if section.lower() not in text.lower()]
assert not missing, f"missing required sections: {missing}"

required_terms = [
    ".env",
    "../nemotron-voice-agent/config/.env",
    "NVIDIA_API_KEY",
    "NVIDIA_LLM_URL",
    "NVIDIA_LLM_MODEL",
    "AGENT_MODEL_NAME",
    "docker compose up --build",
    "docker compose down",
    "python -m pytest",
    "scripts/smoke_voice_connection.py",
]
missing = [term for term in required_terms if term not in text]
assert not missing, f"missing required operational terms: {missing}"

for bad in ["<agent-name>", "<tool_name>", "REPLACE_ME"]:
    assert bad not in text, f"unresolved placeholder: {bad}"

print("generated runnable skill audit PASS")
PY
```

Then read the generated skill and follow its own Start / Smoke Test instructions
for the final Docker validation. This proves the generated runbook is not just
present, but actually usable.

**Checklist**
- [ ] `.agents/skills/<agent-name>/SKILL.md` passes the structural audit above
- [ ] Frontmatter `name` matches the `<agent-name>` directory exactly
- [ ] Required operational sections are present and specific to the generated repo
- [ ] The generated skill documents both env files and refuses to start without them
- [ ] The generated skill points Claude Code and Codex users to copy or symlink
  `.agents/skills/<agent-name>/` into their skill directories if desired
- [ ] Final Docker validation follows the generated skill's Start and Smoke Test
  instructions, not only the creator skill's embedded instructions

---

### Unit tests — tools in isolation

These tests require no LLM and no running server. Run them first.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/test_tools.py -v
```

Each tool must have at least one test in `tests/test_tools.py` that:
- Calls the tool function directly with valid mock inputs and asserts the return shape
- Calls it with missing or malformed inputs and asserts a handled error (not an unhandled exception)

**pytest-asyncio fixture note:** Any `async def` fixture used by async tests must
be decorated with `@pytest_asyncio.fixture` (not the plain `@pytest.fixture`).
Plain `@pytest.fixture` on an async function causes a
`PytestRemovedIn9Warning` error in pytest-asyncio strict mode. Example:
```python
import pytest_asyncio

@pytest_asyncio.fixture
async def client(mock_graph):
    async with AsyncClient(...) as c:
        yield c
```

**Checklist**
- [ ] `tests/test_tools.py` exists and covers every tool in `agent/tools/`
- [ ] All unit tests pass without a live LLM or network calls
- [ ] No bare `except` clauses — all tool errors are caught and logged
- [ ] Async test fixtures use `@pytest_asyncio.fixture`, not `@pytest.fixture`

---

### Integration tests — FastAPI endpoint

Run a deterministic smoke pass first with `LLM_MOCK_MODE=true` so basic server
health does not depend on NVIDIA credentials. Then run the live LLM pass with
`LLM_MOCK_MODE=false` and `NVIDIA_API_KEY` set. These tests do not require
Docker.

```bash
# Terminal 1 — deterministic server smoke, no live LLM call
source .venv/bin/activate
LLM_MOCK_MODE=true python agent/server.py

# Terminal 2 — run integration tests
source .venv/bin/activate
python -m pytest tests/test_server.py -v
```

`tests/test_server.py` must verify:
- `GET /debug/config` returns non-secret effective config
- `POST /v1/chat/completions` with a realistic clinical message returns a 200
  with a valid SSE stream
- Voice-agent-shaped streaming requests return non-empty assistant text for
  simple normal utterances such as `hello` and `Hi I'm here to check in`. Build
  the request like the Nemotron Voice Agent does: `stream: true`, `model:
  AGENT_MODEL_NAME`, and a `messages` array containing the voice-agent
  instruction/context followed by the current user utterance.
- The non-mock graph-backed streaming helper emits at least one spoken SSE chunk
  when a fake graph yields an assistant text chunk. Do not rely only on the
  `LLM_MOCK_MODE=true` branch; that branch can pass while the real graph stream
  path drops all text.
- The stream helper converts cumulative graph chunks into OpenAI-style deltas
  and skips repeated full-message chunks. A fake graph that yields
  `Hello! May I have your name, please?` twice must produce that sentence only
  once in the SSE body.
- The stream terminates with a `data: [DONE]` event
- `GET /health` returns 200
- `GET /v1/models` returns `AGENT_MODEL_NAME`
- Sending a message that should invoke a tool results in the tool being called
  (verify via log output or response content)

**Checklist**
- [ ] `tests/test_server.py` exists and covers all routes above
- [ ] Deterministic `LLM_MOCK_MODE=true` server smoke passes without an API key
- [ ] Voice-agent-shaped greeting smoke cases return non-empty assistant text
  and not a bare guardrail/classifier verdict
- [ ] Integration tests pass against a live LLM with a valid `NVIDIA_API_KEY`
- [ ] SSE stream produces valid JSON chunks and terminates cleanly
- [ ] `/debug/config` contains no secret values

---

### End-to-end — full Docker Compose stack

First render the compose file and confirm the host ports are available:

```bash
docker compose config >/tmp/<agent-name>-compose.yml
python - <<'PY'
import os, socket
for name, default in {"AGENT_PORT": 8000, "VOICE_AGENT_PORT": 7860, "VOICE_AGENT_UI_PORT": 9000}.items():
    port = int(os.getenv(name, default))
    sock = socket.socket()
    try:
        sock.bind(("127.0.0.1", port))
    except OSError as exc:
        raise SystemExit(f"{name}={port} is unavailable: {exc}")
    finally:
        sock.close()
PY
```

Then launch with Docker Compose:

```bash
docker compose up --build
```

Once all services are healthy, run the generated voice connection smoke test and
then open the Docker-published UI at `http://<machine-ip>:9000` in a browser
and run the following manually. If the Docker host UI port was changed, use
`http://<machine-ip>:<VOICE_AGENT_UI_PORT>` instead.

```bash
python scripts/smoke_voice_connection.py
```

1. Speak a complete golden-path scenario (e.g., full patient intake from
   greeting to confirmation) and verify the agent responds correctly at each
   turn
2. Verify audio is heard from the TTS output
3. Verify tool calls appear in the agent backend logs

**Checklist**
- [ ] `TRANSPORT=WEBRTC` set for both `nemotron-voice-agent` and `voice-agent-ui`
- [ ] `agent-backend` health check uses `python` (not `curl`)
- [ ] `nemotron-voice-agent` health check uses `curl -sf http://localhost:7860/docs`
- [ ] `voice-agent-ui` command uses exec form `["python", "-c", "import time; time.sleep(15); exec(open('start-server.py').read())"]` — NOT `sh -c "..."` (frontend image is distroless; no shell available)
- [ ] Port mappings use `${AGENT_PORT:-8000}:${AGENT_PORT:-8000}` (both sides)
- [ ] `nemotron-voice-agent` service is present and active (not commented out)
- [ ] `NVIDIA_LLM_URL` set to `http://agent-backend:${AGENT_PORT:-8000}/v1`
- [ ] `NVIDIA_LLM_MODEL` resolves to the same value as backend `AGENT_MODEL_NAME`
- [ ] All three services on the same docker-compose network
- [ ] `scripts/smoke_voice_connection.py` verifies `/health`, `/v1/models`,
  `/debug/config`, and voice-agent-shaped streaming `/v1/chat/completions`
  requests for `hello` and `Hi I'm here to check in`
- [ ] `docker compose up --build` completes and all services reach healthy state
- [ ] Manual golden-path conversation completes successfully end-to-end

---

### Guardrails validation (only if Phase 2(f) enabled)

Guardrails must be tested in both directions. A suite that only tests blocking
is incomplete — false positives that break normal clinical conversations are
equally important to catch.

**Automated — configuration compatibility**

```bash
python - <<'PY'
import os
from nemoguardrails import RailsConfig

RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
print("guardrails config load PASS")
PY
```

Run this after dependency installation in the generated repo, before Docker
handoff. It catches schema or parameter-key drift for the `nemoguardrails`
version that was actually installed. A failure means the repo is not validated:
update the config expression, update tests, or document the dependency install
failure as a blocker.

**Automated — should-block, should-modify, and should-pass suite**

```bash
python -m pytest tests/test_graph.py tests/test_guardrails.py -v
```

`tests/test_guardrails.py` must include the same config compatibility test and a
parametrized test using the cases captured in `specs/guardrails/spec.md`. The
config test must not use `pytest.importorskip`; if `nemoguardrails` was requested
but cannot be imported after `pip install -r requirements.txt`, validation
should fail. Each behavior case records the rail type, input fixture, expected
status (`block`, `modify`, or `pass`), and expected observable behavior.

Generate this test in `tests/test_guardrails.py` whenever guardrails are enabled:

```python
import os


def test_nemoguardrails_config_loads_with_installed_version():
    from nemoguardrails import RailsConfig

    RailsConfig.from_path(os.getenv("GUARDRAILS_CONFIG_PATH", "config/guardrails"))
```

Do not make this test conditional. It exists specifically to fail before handoff
when the generated config does not match the installed `nemoguardrails` version.

- **Should-block cases**: off-topic requests, adversarial prompts, jailbreak
  attempts, unsafe tool arguments, or untrusted retrieved context. Assert the
  response redirects or refuses rather than answering or executing.
- **Should-modify cases**: PII redaction, output filtering, or context filtering.
  Assert the unsafe content is removed or replaced.
- **Should-pass cases**: legitimate clinical inputs that superficially resemble
  blocked inputs. Assert the agent responds normally without being intercepted.

If guardrails are overly sensitive and block normal replies, work with the
coding agent to add more concrete allow/reject examples to the guardrails prompt
or deterministic guardrail policy. If prompt/example tuning still false-blocks
normal traffic, change to a different LLM powering the guardrails safety checks
and rerun the should-block and should-pass suite.

The LLM can be mocked for block/modify/pass assertions since you are
testing the rails logic, not clinical reasoning.

`tests/test_graph.py` must also include a mocked construction test when the
agent combines ReAct, Guardrails, and tools. Fake `create_react_agent` should
assert the model argument has `bind_tools()`; fake `RunnableRails.__or__` should
assert it receives the bound LLM. This test prevents the runtime failure
`AttributeError: 'RunnableRails' object has no attribute 'bind_tools'`.

`tests/test_guardrails.py` must also cover the selected guardrail
implementation. For deterministic custom action rails, it must import and call
the custom actions directly, prove `hello` and approved intake cases pass, prove
diagnosis/privacy cases block, and assert `config.yml` has no
`self_check_input`, `self_check_output`, or `prompts:` entries for those rails.
For LLM self-check rails, it must check that prompts use parser-compatible
`safe`/`unsafe` wording with `output_parser: is_content_safe`, do not contain
`yes`/`no` verdict instructions, and include task-specific `self_check_input`
and `self_check_output` model entries.
`tests/test_server.py` must check that the response sanitizer removes leaked
leading guardrail verdicts such as `yes.`, `No:`, `safe -`, or `unsafe;` before
text is spoken, and must exercise the non-mock graph stream path with a fake
spoken chunk so an unreachable `yield` or over-filtered metadata fails tests.
It must also exercise repeated full-message chunks and cumulative chunks so the
server never sends duplicated text to the voice UI.

**Manual adversarial testing**

Have a human actively try to break the rails:
- Ask the agent to ignore its instructions
- Steer the conversation off-topic in subtle ways
- Try multi-turn escalation (start on-topic, drift off)

Any new cases that slip through become additional parametrized entries in
`tests/test_guardrails.py`.

**Checklist**
- [ ] `tests/test_guardrails.py` exists with the should-block, should-modify,
  and should-pass cases from `specs/guardrails/spec.md`
- [ ] `tests/test_guardrails.py` includes a non-skipped config compatibility
  test that loads `config/guardrails/` with the installed `nemoguardrails`
  version
- [ ] Config-load compatibility check passes before Docker handoff
- [ ] If the graph uses both Guardrails and tools: `tests/test_graph.py`
  includes a regression test proving the model passed to `create_react_agent`
  exposes `bind_tools()` and does not pass raw `RunnableRails`
- [ ] All should-block cases fire correctly — response redirects or refuses
- [ ] All should-pass cases flow through without interception
- [ ] Manual adversarial session completed; any bypasses added to the test suite
- [ ] Guardrails latency is measured and documented; output or dynamic rails may add noticeable voice latency
- [ ] Every SC-XXX criterion in `specs/guardrails/spec.md` is traceable to a
  test case or observable behavior

---

### Final checklist

**Code correctness**
- [ ] Agent server starts without errors: `python agent/server.py`
- [ ] Static checks pass: `compileall`, server import smoke, `docker compose config`, and placeholder scan
- [ ] If guardrails enabled: `nemoguardrails` is present in `requirements.txt`
- [ ] If guardrails enabled: generated guardrails config loads through
  `RailsConfig.from_path(...)` with the installed `nemoguardrails` version
- [ ] No placeholder TODOs remain in source code
- [ ] No hardcoded configurable port numbers in source, config, or compose files; only the fixed WebRTC target `7860` and UI container target `8000` are allowed literals
- [ ] `/v1/models` uses `AGENT_MODEL_NAME`, not a hardcoded stale model id
- [ ] `/debug/config` reports effective non-secret config for troubleshooting
- [ ] `LLM_MOCK_MODE=true` produces a deterministic response for local smoke tests and defaults to `false`
- [ ] `LLM_ENABLE_THINKING` only wired into the API call when model supports it
- [ ] `LLM_MAX_TOKENS` ≥ 8192 when thinking is enabled
- [ ] All six agent events logged at correct level (request received, tool call, tool result, LLM response, stream complete, unhandled exception)
- [ ] `LOG_LEVEL` env var wired and defaults to `INFO`
- [ ] PII field values redacted in tool-call and request-received log lines

**Configuration**
- [ ] `.env.example` lists every required variable with defaults and comments
- [ ] `.env.example` includes `AGENT_MODEL_NAME`, `AGENT_PORT`, `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`, `LLM_MOCK_MODE`, and `LOG_LEVEL`
- [ ] Developer confirmed `my-custom-ambient-healthcare-agent/.env` was filled in before proceeding to Nemotron Voice Agent configuration
- [ ] Developer confirmed `nemotron-voice-agent/config/.env` was filled in before `docker compose up --build` was run
- [ ] Both docs paths show Docker Compose and manual-local `NVIDIA_LLM_URL` values
- [ ] `AGENT_PORT` and `VOICE_AGENT_UI_PORT` are flexible; `VOICE_AGENT_PORT=7860` is documented as fixed for WebRTC
- [ ] `NVIDIA_LLM_MODEL`, `/v1/models`, and `AGENT_MODEL_NAME` use the same generated agent id

**Documentation**
- [ ] Human-readable `README.md` exists and includes Docker Compose setup first, local venv for tests second
- [ ] README Getting Started configures both `.env` and `../nemotron-voice-agent/config/.env` before any startup command
- [ ] README includes `git clone --recurse-submodules` step for `../nemotron-voice-agent`
- [ ] README documents nemotron env var configuration
- [ ] README references the `nemotron-voice-agent-deploy` skill for hardware-specific deployments
- [ ] README states that all three model services default to NVIDIA public cloud endpoints and documents how to override each to a self-hosted NIM
- [ ] README notes "No voices found" cosmetic issue and VOICE_AGENT_PORT=7860 constraint
- [ ] README and runnable skill include the Chrome microphone prerequisite:
  enable "Insecure origins treated as secure", add `http://<machine-ip>:9000`,
  and restart Chrome before using the remote WebRTC UI
- [ ] Agent-readable `.agents/skills/<agent-name>/SKILL.md` exists and covers all key workflows for coding agents (agentskills.io compliant)
- [ ] `.agents/skills/<agent-name>/SKILL.md` has a Start section that checks both env files and stops if required values are missing
- [ ] `.agents/skills/<agent-name>/SKILL.md` passed the generated runnable skill adequacy audit
- [ ] Final Docker validation followed the generated skill's own Start and Smoke Test instructions
- [ ] README and runnable skill keep `docker compose up --build` as the launch command; no wrapper command is required
- [ ] Final handoff redirects the developer to the newly created `README.md`
  Getting Started / Quick Start instructions as the human-readable source of truth
- [ ] Final handoff tells the developer to point Claude Code, Codex, or another
  coding agent at the newly created `.agents/skills/<agent-name>/SKILL.md`
- [ ] Final handoff clearly states that `.env` and
  `../nemotron-voice-agent/config/.env` must be configured before running the repo
- [ ] Final handoff explains the model-identity contract:
  `NVIDIA_LLM_MODEL` in the Nemotron Voice Agent repo must match
  `AGENT_MODEL_NAME` in the generated backend and the `/v1/models` id
- [ ] Final handoff relays the Chrome microphone prerequisite before the user
  opens the web UI

**Spec coverage**
- [ ] Every SC-XXX criterion in `specs/langgraph-agent/spec.md` is traceable to a test or observable behavior
- [ ] Every SC-XXX criterion in `specs/fastapi-server/spec.md` is traceable to a test or observable behavior
- [ ] If guardrails enabled: every SC-XXX criterion in `specs/guardrails/spec.md` is traceable to a test or observable behavior
- [ ] Any unmet criterion is listed as a known gap with a follow-up issue

---

### Final handoff to developer

After every validation checklist item passes, close with a concrete handoff. Do
not stop at "tests passed." The final message must include:

1. **Human getting-started path**
   - Point the developer to `README.md`, specifically the Quick Start / Getting
     Started section.
   - Say that this is the human-readable source of truth for first-run setup.
   - Do this as a redirect to the newly created README, not by duplicating the
     entire README in the final answer.

2. **Coding-agent path**
   - Point Claude Code, Codex, and other coding agents to the generated
     agent-readable skill:
     `.agents/skills/<agent-name>/SKILL.md`
   - Use this exact path shape. The `SKILL.md` file lives inside the
     `<agent-name>` directory; the path is not
     `.agents/skills/<agent-name>.SKILL.md`.
   - If a coding-agent product requires installed skills, tell the developer
     they can copy or symlink `.agents/skills/<agent-name>/` to:
     - Claude Code: `~/.claude/skills/<agent-name>`
     - Codex: `~/.codex/skills/<agent-name>`
   - Tell them to restart Claude Code or Codex after installing so the skill
     inventory refreshes.

3. **Mandatory environment setup**
   - State plainly that the repo will not run until both env files are
     configured:
     - Generated backend: `.env` copied from `.env.example`
     - Nemotron Voice Agent: `../nemotron-voice-agent/config/.env`
   - List the backend `.env` values to fill or confirm:
     `NVIDIA_API_KEY`, `AGENT_MODEL_NAME`, `LLM_MODEL`, `LLM_BASE_URL`,
     `LLM_ENABLE_THINKING`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`,
     `LLM_MOCK_MODE`, `AGENT_PORT`, `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`,
     `LOG_LEVEL`, and any generated feature-specific keys.
   - List the Nemotron Voice Agent `config/.env` values to fill or confirm:
     `NVIDIA_API_KEY`, `NVIDIA_LLM_URL`, `NVIDIA_LLM_MODEL`,
     `TRANSPORT=WEBRTC`, and required ASR/TTS keys from the voice-agent
     `env.example`.
   - Explain `NVIDIA_LLM_URL`: it is the OpenAI-compatible endpoint the
     Nemotron Voice Agent calls. In Docker Compose it must be
     `http://agent-backend:${AGENT_PORT:-8000}/v1` so the voice stack calls the
     generated backend rather than a raw NIM.
   - Explain `NVIDIA_LLM_MODEL`: it is the model id the Nemotron Voice Agent
     sends to `/v1/chat/completions`.
   - Tell the developer to comment out any existing active `NVIDIA_LLM_URL` or
     `NVIDIA_LLM_MODEL` lines in `../nemotron-voice-agent/config/.env` before
     adding the generated values. The upstream env file contains model option
     blocks, and leaving multiple active settings can route requests to the
     wrong endpoint or model id.
   - Explain that `NVIDIA_LLM_MODEL` in
     `../nemotron-voice-agent/config/.env` must exactly match
     `AGENT_MODEL_NAME` in the generated backend `.env`, and that the backend
     exposes the same id from `/v1/models`. The Nemotron Voice Agent sends this
     model id in chat-completion requests, so a mismatch can make the voice
     stack call a model name the backend is not advertising.

4. **Browser microphone prerequisite**
   - Relay this exact note before telling the user to open the web UI:
     `Note: To enable microphone access in Chrome, go to chrome://flags/, enable
     "Insecure origins treated as secure", add http://<machine-ip>:9000 to the
     list, and restart Chrome.`

Use this final-response shape:

> "Validation passed. Start with `README.md` -> Quick Start / Getting Started
> for the human setup flow.
>
> For coding agents, point Claude Code, Codex, or another agent at
> `.agents/skills/<agent-name>/SKILL.md`. That file is the agent-readable
> runbook for starting, testing, stopping, and troubleshooting this repo. To
> install it as a reusable skill, copy or symlink `.agents/skills/<agent-name>/`
> to `~/.claude/skills/<agent-name>` for Claude Code or
> `~/.codex/skills/<agent-name>` for Codex, then restart the agent session.
>
> Before running `docker compose up --build`, configure both env files.
>
> In this repo's `.env`, fill or confirm: `NVIDIA_API_KEY`,
> `AGENT_MODEL_NAME`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_ENABLE_THINKING`,
> `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_MOCK_MODE`, `AGENT_PORT`,
> `VOICE_AGENT_PORT`, `VOICE_AGENT_UI_PORT`, `LOG_LEVEL`, and any generated
> feature-specific keys.
>
> In `../nemotron-voice-agent/config/.env`, fill or confirm:
> `NVIDIA_API_KEY`, `NVIDIA_LLM_URL`, `NVIDIA_LLM_MODEL`, `TRANSPORT=WEBRTC`,
> and required ASR/TTS keys from the voice-agent `env.example`.
> `NVIDIA_LLM_URL` is the OpenAI-compatible endpoint the voice agent calls for
> chat completions. For Docker Compose, set it to
> `http://agent-backend:${AGENT_PORT:-8000}/v1` so the voice stack routes
> through this generated backend. `NVIDIA_LLM_MODEL` is the model id sent with
> each chat-completion request. It must match backend `AGENT_MODEL_NAME` and the
> id returned by `/v1/models`.
>
> In `../nemotron-voice-agent/config/.env`, comment out any existing active
> `NVIDIA_LLM_URL` or `NVIDIA_LLM_MODEL` lines before adding the generated
> values. The upstream env file includes model option blocks, so there should be
> exactly one active `NVIDIA_LLM_URL` and exactly one active
> `NVIDIA_LLM_MODEL`.
>
> Note: To enable microphone access in Chrome, go to chrome://flags/, enable
> "Insecure origins treated as secure", add http://<machine-ip>:9000 to the
> list, and restart Chrome."

---
