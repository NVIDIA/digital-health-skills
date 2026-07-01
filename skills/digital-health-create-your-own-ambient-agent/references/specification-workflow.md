# Specification Workflow

Use this reference for Phase 2. It covers the required developer questions,
feature-spec creation, guardrails selection, and approval gates before planning.

## Contents

- Phase 2: Specify
- Voice interface and output location
- Agent functionality and data sources
- LangGraph graph pattern
- LLM model configuration
- Optional NeMo Guardrails
- Service endpoints
- Feature spec writing for `langgraph-agent`, `fastapi-server`, and optional
  `guardrails`

## Phase 2: Specify

### Developer-facing prompt fidelity

When this workflow marks a prompt as **verbatim**, send the full prompt exactly
as written. Do not condense, reword, merge with surrounding context, replace
the examples, or change the order. You may add only a short transition sentence
before the verbatim prompt if needed for conversation continuity.

Start by orienting the developer to the spec-kit structure this skill uses:

> "Before we write any code, we capture what to build and how to build it in a
> set of spec files. This skill uses the spec-kit format: each feature gets its
> own directory with three files — `spec.md` (what), `plan.md` (how),
> `tasks.md` (ordered task list). I've included pre-written examples in this
> skill: `references/spec-examples/langgraph-agent/`,
> `references/spec-examples/fastapi-server/`, and optional
> `references/spec-examples/guardrails/` — take a look to see what complete
> triplets look like."

We produce specs for two fixed features — the LangGraph agent and the FastAPI
server + Docker deployment — plus a third `guardrails` feature only when the
developer enables NeMo Guardrails. Work through items (a)–(g) below, then write
the feature specs.

After all seven questions are answered, write the following in the output repo:

```
specs/
  langgraph-agent/
    spec.md    ← user stories, FR-XXX requirements, SC-XXX success criteria, assumptions
    plan.md    ← tech stack, chosen graph pattern, tool contract, reference files
    tasks.md   ← phased tasks: setup → tools (parallel) → graph → polish
  fastapi-server/
    spec.md    ← user stories for /v1/chat/completions, docker-compose, port config
    plan.md    ← API contract, Docker Compose architecture, health check rules, .env.example
    tasks.md   ← phased tasks: server → tests (parallel) → Docker → validation
  guardrails/  ← only if Phase 2(f) enabled
    spec.md    ← selected rail types, rules, examples, latency assumptions
    plan.md    ← RunnableRails/LangGraph integration, config files, test strategy
    tasks.md   ← config → graph wiring → guardrails tests → validation
```

Each `spec.md` must follow the spec-kit format:
- **User Scenarios & Testing** — prioritized user stories with Given/When/Then
  acceptance scenarios and an independent test description per story
- **Requirements** — FR-001…FR-N using MUST/SHOULD/MAY (RFC 2119); Key Entities
  subsection for data models
- **Success Criteria** — SC-001…SC-N measurable outcomes
- **Assumptions** — fixed technical constraints (architecture, LLM defaults,
  service endpoints, known limitations)

Present each feature's spec to the developer with an Approval Brief and ask for
approval before writing its `plan.md`. Present each `plan.md` before writing its
`tasks.md`.

### Approval Brief requirement

Before asking for approval for any generated `spec.md`, read back the file that
was just written and provide a short Approval Brief. The brief must summarize
the actual file contents, not just the conversation or intended design.

Use only the items that are relevant to that file:

- **File**: path and one-sentence purpose
- **What it covers**: main sections, workflows, or implementation areas included
- **Key choices captured**: important decisions, assumptions, defaults, or
  user-provided choices
- **Important details to review**: fields, APIs, data handling, task ordering,
  constraints, or acceptance criteria that most affect the outcome
- **Dependencies or sequencing**: anything this file depends on, unlocks, or
  requires before the next phase
- **Open questions or risks**: only include if the file leaves something
  unresolved
- **Approval request**: ask whether to approve as written or revise before
  continuing

Keep the brief concise. Do not force every category to appear; omit irrelevant
items and combine related points when the file is simple.

**Do not proceed to Phase 3 until the developer has approved all spec.md files.**

### (a) Voice Interface

Confirm with the developer:

> "For the voice interface we will use the **NVIDIA Nemotron Voice Agent**
> (github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent). This provides
> real-time WebRTC audio, ASR, and TTS. Please confirm to proceed, or describe
> an alternative."

Wait for confirmation.

Once the developer confirms, ask where the output repo should live — you need
this now so the Nemotron Voice Agent repo can be cloned parallel to it:

> "Where should we create your agent backend repo? Paste an absolute path, or
> type `default` to use the current directory. I will create
> `my-custom-ambient-healthcare-agent/` there and clone the Nemotron Voice Agent
> alongside it."

Once confirmed, immediately clone the Nemotron Voice Agent:

```bash
git clone --recurse-submodules \
  https://github.com/NVIDIA-AI-Blueprints/nemotron-voice-agent \
  <output-parent>/nemotron-voice-agent
```

Where `<output-parent>` is the directory the developer chose (or the current
directory if they typed `default`). This establishes the sibling layout that the
docker-compose relies on:

```
<output-parent>/
├── my-custom-ambient-healthcare-agent/   ← written in Phase 4
└── nemotron-voice-agent/                 ← cloned now
```

Store `<output-parent>` — it is used throughout Phases 3 and 4.

### (b) Agent Functionality

Ask the developer to list every function they want the agent to perform. Use
this prompt **verbatim** as the user-facing question for this step:

```text
What should your agent be able to do? List every capability, even rough ideas. You can specify your own agent capability. If you're not sure yet, choose one in the following example use cases.


Here are the examples:

1. "Use case: Patient intake. Data IO: Save each completed intake as a JSON
   file. Intake fields: patient name, date of birth, current symptoms, current
   pharmacy."
2. "Use case: Appointment making. Data IO: Read available appointment slots
   from SQLite and write confirmed bookings with patient name, date of birth,
   preferred clinician, visit reason, and confirmation number."
3. "Use case: Prescription refill requests. Data IO: Read active medications
   from SQLite, and write refill requests with medication name, dosage, 
   preferred pharmacy, and status."
4. "Use case: Clinical FAQ. Data IO: Retrieve answers from a clinical FAQ
   knowledge base and cite the source document used."
```

Capture the full list before continuing.

### (c) Data Source

For each function from (b) that requires data, ask which backend to use:

- **SQLite** — local file, zero infrastructure, great for demos
- **JSON files** — local structured file IO for simple append/update workflows
- **NVIDIA RAG (NIM + Milvus)** — vector search over clinical documents
- **Tavily web search** — live web search for general medical information
- **Mock / hardcoded** — in-memory fixtures for prototyping
- **Custom** — developer specifies their own

Ask: "For functions that need stored or retrieved data, which data backend fits best?"

Capture the choice(s) before continuing.

### (d) LangGraph Graph Pattern

Inform the developer that LangGraph is the fixed agent framework:

> "The agent backend will be built with **LangGraph** — this is fixed and not
> configurable. Within LangGraph, you choose the graph pattern that best fits
> your clinical workflow. By default, I recommend using **ReAct** unless you
> specifically want one of the other patterns:
>
> 1. **ReAct (default recommended choice)** — Uses LangGraph's
>    `create_react_agent` prebuilt. The LLM decides when to call tools in a
>    loop. Best for: collecting patient information, looking up records,
>    answering questions with data retrieval.
>
> 2. **Custom graph with conditional routing** — You define explicit nodes
>    (Python functions) and edges (routing logic). The LLM runs at one or more
>    nodes; Python code decides what happens next. Best for: multi-step clinical
>    workflows with defined decision points (e.g., triage → intake → referral).
>
> 3. **Sequential workflow** — Nodes execute in a fixed order; the LLM generates
>    output at one or more stages. Best for: structured document generation,
>    report filling, or pipelines where the steps never branch.
>
> Unless you specifically want a custom graph or sequential workflow, should we
> use the default ReAct pattern? You can also describe your workflow and I will
> recommend a different pattern if it fits better."

Capture the pattern choice and the reasoning. This drives the graph implementation
in `agent/graph.py` and the plan for the `langgraph-agent` feature.

### (e) LLM Model

Present the default and explain alternatives:

> "Which LLM should power the agent's reasoning?
>
> **Default (recommended):** `nvidia/nemotron-3-super-120b-a12b` via
> `https://integrate.api.nvidia.com/v1`. This is the default LLM that will power
> the generated agent unless you choose another one.
>
> Do you wish to choose another LLM? You can browse `build.nvidia.com` to find
> available NVIDIA models, or specify a local NIM or external provider model.
> Type the model name and base URL, or type `default` to accept the default."

Capture and confirm these four values:

| Parameter | Default |
|---|---|
| Model name | `nvidia/nemotron-3-super-120b-a12b` |
| Base URL | `https://integrate.api.nvidia.com/v1` |
| API key env var | `NVIDIA_API_KEY` |
| Thinking/reasoning enabled | `true` (if model supports it) |

If the selected model supports thinking mode, ask whether to enable it.
Set `LLM_MAX_TOKENS` to at least `8192` when thinking is on.

### (f) Guardrails (optional)

Before asking about Guardrails, **always do a live read of the official NVIDIA
NeMo Guardrails docs**. Do not rely only on the cloned reference repo, this
skill's embedded examples, or model memory for the rail type list.

Open these live docs and summarize only the current rail type options:

- `https://docs.nvidia.com/nemo/guardrails/latest/about/rail-types.html`
- `https://docs.nvidia.com/nemo/guardrails/latest/configure-rails/yaml-schema/guardrails-configuration/index.html`
- `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/runnable-rails.html`
- `https://docs.nvidia.com/nemo/guardrails/latest/integration/langchain/langgraph-integration.html`

If the live docs differ from the rail list embedded below, use the live docs as
the source of truth, update the summary before showing it to the developer, and
record the difference in `specs/guardrails/plan.md`.

Then ask the developer whether to add NVIDIA NeMo Guardrails:

> "Do you want to add NeMo Guardrails to your agent? Guardrails run inside the
> LangGraph graph using NeMo `RunnableRails`, so the same integration point can
> support any rail types you configure.
>
> I just checked the live NVIDIA NeMo Guardrails docs. The current rail type
> options are:
>
> 1. **Input rails** — validate or sanitize user input before a model call.
> 2. **Output rails** — filter, redact, or block model responses before the user
>    hears them.
> 3. **Dialog rails** — enforce multi-turn conversation flow using Colang.
> 4. **Retrieval rails** — validate retrieved documents or chunks before they are
>    used as model context.
> 5. **Execution rails** — validate tool/action calls, arguments, or results.
>    In current NeMo Guardrails configs, these are implemented with
>    `rails.execution.flows`.
>
> Input and output rails are the most common. If you are new to guardrails or
> could not decide on what type of guardrails to implement, you could start with
> input rails only and add more later on.
>
> You can enable any combination, all five, or none. Type **all** for every rail
> type, type **skip** or **none** to proceed without guardrails, or describe
> which rail types you want and any specific rules."

Normalize the answer into `selected_guardrail_types`:
- `all` → `["input", "output", "dialog", "retrieval", "execution"]`
- `skip`, `none`, or an explicit no → `[]`
- Otherwise map the developer's wording onto any subset of `input`, `output`,
  `dialog`, `retrieval`, and `execution`; confirm the normalized list before
  asking the follow-up Guardrails questions.

If the developer skips, note it and continue. No guardrails files will be
generated and `test_guardrails.py` will be omitted. Skip directly to (g).

If the developer opts in, work through the sub-questions below in order.

#### (f-i) Rail behavior

> "Which guardrails should this agent enforce? Describe the behavior you want
> for input, output, dialog, retrieval, and/or execution rails. For example:
> block jailbreak attempts, redirect off-topic requests, require patient identity
> confirmation before scheduling, filter untrusted retrieved chunks, or validate
> tool arguments before execution.
>
> Output rails can add voice latency because the response may need to be checked
> before TTS speaks it. Use output rails when the agent can expose sensitive data
> or must redact final answers."

Capture the selected rail types and rules. Store them in
`specs/guardrails/spec.md`; they drive the `rails:` section in `config.yml`,
Colang files, custom actions, and test coverage.

**Fixed implementation note (record in the spec Assumptions):**
Guardrails are always applied with `RunnableRails` inside `agent/graph.py`. Do
not implement the optional guardrails path with `LLMRails.check_async()` in
`server.py`, and do not use LangChain `GuardrailsMiddleware`. `RunnableRails` is
the single integration mode for this skill because it composes with LangGraph
and can support any rail type configured in NeMo Guardrails. For tool-calling
agents, bind tools to the LLM first and use `RunnableRails(..., passthrough=True)`
in the model runnable path. Do not pass a raw `RunnableRails` object or
`guardrails | llm.bind_tools(tools)` directly to `create_react_agent` for
tool-calling ReAct graphs: current LangGraph calls `.bind_tools()` on the model
argument during agent construction, and `RunnableRails` does not expose that
method. Generate either a small adapter whose `bind_tools()` returns
`guardrails | llm.bind_tools(tools)`, or switch the graph to an explicit
`StateGraph` with a guarded model node and `ToolNode`.

**Streaming trade-off:** `RunnableRails` supports streaming when used directly,
but the current NeMo Guardrails LangGraph integration may emit one larger chunk
after rail processing instead of preserving token-by-token graph streaming. Keep
the FastAPI SSE contract intact either way. If the developer selects output,
dialog, retrieval, or execution rails, document the expected voice latency and
test for valid SSE framing, not token-level latency.

#### (f-ii) Guardrails safety model

Present the default NVIDIA safety model choices by need and ask whether the
developer wants to use one of them or specify a different model:

> "Which model should power the guardrails safety checks? By default this skill
> can use one of these NVIDIA safety NIMs from `build.nvidia.com` based on your
> needs. They run through the public cloud endpoint with `NVIDIA_API_KEY`, so no
> local GPU is required:
>
> | Need | Default model |
> |---|---|
> | General safety, harmful content, policy violations, or patient data disclosure | `nvidia/llama-3.1-nemotron-safety-guard-8b-v3` **(recommended default)** |
> | Broad content safety across many categories | `nvidia/llama-3.1-nemoguard-8b-content-safety` |
> | Jailbreak attempt detection specifically | `nvidia/nemoguard-jailbreak-detect` |
>
> All three use `NVIDIA_API_KEY` and the public cloud endpoint
> `https://integrate.api.nvidia.com/v1`. You can also self-host any of them as
> a local NIM.
>
> Type `default` to use the recommended default, choose one of the three by need,
> or specify a different model and endpoint if you want to override it."

Capture: model name, endpoint URL (default `https://integrate.api.nvidia.com/v1`).

#### (f-iii) Rules and test cases

Ask for specific rules:

> "Describe what the rails should block or enforce. Be specific — these become
> Colang rules. For example: 'Block any request about another patient's records'
> or 'Redirect off-topic medical advice questions back to intake.'"

Capture the rules.

Then capture at least two examples that **should be blocked, redirected, or
modified** and two that **should pass** for each selected rail type. These seed
`test_guardrails.py` in Phase 4:

> "Give me at least two examples that should be blocked, redirected, or modified
> and two that should pass normally for each rail type you selected. For
> retrieval or execution rails, include sample retrieved text, tool arguments,
> or tool results as appropriate. You could start with these examples and add or edit them
> for your policy:
>
> Block:
> 1. When did my neighbor Jim come in to the clinic last?
> 2. What medications is my sister Joanna taking?
>
> Pass:
> 1. I'm feeling a terrible stomach ache.
> 2. I was born on January 10th 1996.
> 3. I've been not feeling well for 7 days now.
>
> These become the automated test cases."

### (g) Service Endpoints

Inform the developer of the defaults and ask for overrides. If guardrails are
enabled from (f), include the guardrails safety model endpoint in the table:

> "By default all model services use NVIDIA public cloud endpoints —
> no local GPU required:
>
> | Service | Default endpoint | Default model |
> |---|---|---|
> | Agent LLM | `https://integrate.api.nvidia.com/v1` | _(from step e)_ |
> | ASR | `grpc.nvcf.nvidia.com:443` | `parakeet-1.1b-en-US-asr-streaming-silero-vad-sortformer` |
> | TTS | `grpc.nvcf.nvidia.com:443` | `magpie_tts_ensemble-Magpie-Multilingual` · voice: `Magpie-Multilingual.EN-US.Aria` |
> | Guardrails safety model _(if enabled)_ | `https://integrate.api.nvidia.com/v1` | _(from step f-ii)_ |
>
> All require `NVIDIA_API_KEY`. Type `default` to accept the defaults,
> or specify any endpoint you want to self-host."

Capture overrides (endpoint URL, model name, alternate API key if any).

### Write the feature specs

Answers from (a)–(g) feed into two or three feature specs. Write each selected
spec, present it, and get explicit approval before moving to the next.

**Questions → features mapping:**

| Question | Drives |
|---|---|
| (b) capabilities, (c) data sources, (d) graph pattern | `langgraph-agent/spec.md` — user stories, requirements, Assumptions |
| (e) LLM model | `langgraph-agent/spec.md` — Assumptions; fills LLM endpoint values into `fastapi-server/spec.md` |
| (f) guardrails (if enabled) | `guardrails/spec.md` — selected rail types, safety model, Colang rules/actions, should-block/modify/pass test cases |
| (g) service endpoints | `fastapi-server/spec.md` — Assumptions (ASR/TTS/guardrails endpoint values) |
| (a) voice interface | confirmation only; does not change either spec unless developer objects |

---

#### Feature 1: `langgraph-agent`

Draft `specs/langgraph-agent/spec.md` in the output repo. Use
`references/spec-examples/langgraph-agent/spec.md` in this skill as the
structural model. Fill in:

- **User Scenarios & Testing**: one user story per capability from (b); each with
  Given/When/Then acceptance scenarios and an independent test description; mark
  priority P1/P2 by clinical importance
- **Requirements**: FR-XXX per capability using MUST/SHOULD/MAY; add a Key
  Entities subsection for any data schema from (c)
- **Success Criteria**: SC-XXX measurable outcomes — one per user story at minimum
- **Assumptions**: LangGraph as the fixed agent framework; LLM config from (e);
  graph pattern chosen in (d) with a brief rationale; tool authoring contract
  (applies to all graph patterns)

Present the drafted spec with an Approval Brief and ask:

> "Here is `specs/langgraph-agent/spec.md` — the spec for your agent's
> clinical capabilities. Each capability from your list is a user story with
> acceptance scenarios. Does this accurately capture what you want to build?
> Please review and let me know any changes."

**Wait for explicit approval before writing `langgraph-agent/plan.md`.**

---

#### Feature 2: `fastapi-server`

The `fastapi-server` spec is pre-written — the API contract, Docker Compose
structure, and integration rules are fully determined by the fixed architecture.
Copy `references/spec-examples/fastapi-server/spec.md` from this skill into the
output repo and fill in only the Assumptions section with the developer's
choices from (e) and (f):
LLM endpoint and model, ASR endpoint and model, TTS endpoint, voice ID, and
language.

Present the filled spec with an Approval Brief and ask:

> "The FastAPI server spec is pre-defined by the architecture — the API contract,
> Docker Compose structure, and health check rules don't change. I've filled in
> your chosen endpoints in the Assumptions section. Does this look correct, or
> do you have major architectural changes you want to make to the server itself?"

Only modify the spec if the developer explicitly requests structural changes
(e.g., adding a non-standard route, changing the streaming protocol). Endpoint
and model name updates are not structural changes — they go in `.env` only.

**Wait for explicit approval before writing `fastapi-server/plan.md`.**

---

#### Feature 3: `guardrails` (only if Phase 2(f) enabled)

Skip this feature entirely if the developer chose not to add guardrails.

Draft `specs/guardrails/spec.md` in the output repo. Use
`references/spec-examples/guardrails/spec.md` in this skill as the structural
model and include only the rail types selected in Phase 2(f). It must cover:

- **User Scenarios & Testing**: one user story per rail type enabled; each with
  Given/When/Then scenarios that cover both the blocked case and the legitimate
  pass-through case
- **Requirements**: FR-XXX rules using MUST (e.g., off-topic inputs MUST be
  redirected); include the Colang rule definitions and custom actions as Key
  Entities; include every selected NeMo rail type as a requirement; document why
  output rails can add voice latency and when they are appropriate
- **Success Criteria**: SC-XXX with explicit should-block, should-modify, and
  should-pass examples sourced from the developer's answers in Phase 2(f)
- **Assumptions**: `nemoguardrails` package (pip install name); integration
  point (`RunnableRails` in `agent/graph.py` with `passthrough=True` for
  tool-calling — NOT `LLMRails.check_async()` in `server.py` and NOT
  `GuardrailsMiddleware`); safety model from Phase 2(f-ii); Colang file
  locations; selected rail types; whether output rails are enabled and their
  latency trade-off

Present the spec with an Approval Brief and ask:

> "Here is `specs/guardrails/spec.md`. It captures the rail types you chose,
> the Colang rules that enforce them, and test cases for both directions —
> what should be blocked and what should pass through. Does this match your
> intent?"

**Wait for explicit approval before writing `guardrails/plan.md`.**

**Do not proceed to Phase 3 until all approved spec.md files are complete
(two if guardrails skipped from (f), three if enabled).**

---
