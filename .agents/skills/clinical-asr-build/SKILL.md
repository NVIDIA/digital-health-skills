---
name: "clinical-asr-build"
description: "Stage 2 of the Clinical ASR Flywheel (self-contained): specialty interview, term curation, two-tier IPA tagging, NeMo-format manifest synthesis. Inlines a Magpie TTS NVCF recipe (SSML phoneme wrapping, voice IDs, rate-limit backoff) and a sentence-generation prompt template — no upstream skill dependency. Preceded by /clinical-asr-setup, followed by /clinical-asr-eval."
version: "1.0.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - dataset
  - ipa
  - magpie
  - nemo-manifest
  - flywheel
  - self-contained
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "Self-contained — requires only NVIDIA_API_KEY (build.nvidia.com), Python 3.10+, and nvidia-riva-client. Sentence generation prefers an LLM (any OpenAI-compatible endpoint or NVCF LLM) but works in template-fallback mode without one. Stage 1 (/clinical-asr-setup) must have been completed first."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  team: healthcare-tme
  domain: ai-ml
  stage: 2
  variant: self-contained
  previous_skill: clinical-asr-setup
  next_skill: clinical-asr-eval
---

# Clinical ASR Flywheel — Stage 2 (Build the benchmark)

You are the **curate-and-synthesize** stage. The user arrives from `/clinical-asr-setup` and leaves with a NeMo-format `manifest.jsonl` plus the audio it references — both ready for scoring at `/clinical-asr-eval`.

Be conversational. This is the warmest, most domain-aware step in the flywheel: you're asking a clinician (or someone who works with them) which terms hurt today and shaping a benchmark around their reality. Ask short, focused questions. Show the user what's being added. Don't lecture.

**Self-contained:** the Magpie TTS recipe and the sentence-generation prompt template are inlined below — there is no `/read-aloud` or `/data-designer` call.

## Purpose

Curate a clinical-specialty term list, generate eval audio for it through Magpie TTS with a two-tier IPA pipeline, and write a NeMo-format manifest tagged with the clinical-extension fields (`term`, `entity_category`, `ipa_source`, `voice_id`, `noise_level`, `context_type`). The output is the input to Stage 3.

By the end the user has:

```
$EVAL_DIR/cycle<N>/
├── audio/<slug>.wav        synthesized clips
├── manifest.jsonl          NeMo format + clinical extension
├── term_seed.csv           the curated input
└── pronunciation_overrides.csv   appendable across cycles
```

(`$EVAL_DIR` is the user's own choice — this skill does not impose a layout.)

## When to use this skill

Activate on user phrases like:

- "Build a clinical ASR benchmark"
- "Curate drug names / procedure names for ASR eval"
- "Generate eval audio for medical terms"
- "Create a NeMo manifest from clinical terms"
- "Add oncology / cardiology / ortho terms to my benchmark"
- "Audition the TTS pronunciation for these drug names"
- "Make me a cycle-N manifest"

Do **not** activate when:

- The user already has a manifest and wants to score it → `/clinical-asr-eval`
- The user wants to fine-tune on an existing manifest → `/clinical-asr-finetune`
- The user is asking about generic synthetic data outside the clinical-ASR loop

## Prerequisites

- **`/clinical-asr-setup` completed** — `NVIDIA_API_KEY` exported, Python deps installed, round-trip self-test passed.
- **An LLM endpoint** for the sentence-generation step. Any OpenAI-compatible chat endpoint works; the recipe below assumes one. Template fallback (no LLM) is documented in Step 2b for offline use.

## Workflow

### 2a. Specialty interview → `term_seed.csv`

Ask **one question at a time**. The goal is to surface 4–10 candidate terms with the right `entity_category`, not to write a textbook.

Questions, in order:

1. *What specialty / workflow is this for?* (oncology dictation, ICU handoff, psych intake, ortho post-op, …)
2. *What ASR failure modes have you seen?* — drug names, multi-word procedures, abbreviations, compound conditions.
3. *Which terms come up daily vs which are the hard ones?* — daily-common terms become the sanity baseline; daily-hard terms become the signal.

Propose 4–10 candidate terms with `entity_category`. Confirm with the user before writing. Then write `term_seed.csv`:

```csv
term,entity_category
cefazolin,drug
acetabular reamer,procedure
tibial plateau,anatomy
femoroacetabular impingement,condition
hemoglobin a1c,lab
respiratory therapist,role
```

**The category vocabulary is fixed.** KER keys off it. Allowed values:

```
drug | procedure | anatomy | condition | lab | role
```

If the user proposes a new category, push back: either it maps to one of the six, or the methodology needs a deliberate extension (which is a future cycle's job, not a one-off ad-hoc add).

### 2b. Sentence generation

Generate 3–5 natural English sentences embedding each term, varying `context_type`. The prompt template below is field-tested against Nemotron-Nano and works across most instruction-tuned LLMs.

**Prompt template** (Jinja-2 style; substitute `{{term}}`, `{{entity_category}}`, `{{context_type}}` per row):

```
You are generating synthetic medical audio transcription text.

Given the term "{{term}}" (category: {{entity_category}}), generate ONE
realistic sentence in the "{{context_type}}" clinical style:
- dictation: structured clinical note (discharge summary, radiology report)
- instruction: verbal clinical order (nurse handoff, dosing instruction)
- narrative: ambient ward conversation (bedside, ward round)
- history: medication reconciliation or patient history taking

Rules:
1. Use the exact term as written: {{term}} (must appear in the sentence)
2. Keep it clinically plausible — exactly ONE sentence, no PII
3. Spell out ALL numbers in words (e.g. "twenty milligrams" not "20mg")
4. Spell out ALL medical abbreviations in full natural language
   (e.g. "intravenous" not "IV", "every eight hours" not "q8h")
5. Write the way a clinician would SPEAK aloud, not how they would type in a chart
6. Do NOT include asterisks, bullet points, dividers (------ or ******),
   section headers, markdown formatting, parentheticals, or stage directions
7. Do NOT produce multiple candidate sentences or alternatives
8. No quotes, no leading labels, no trailing notes — just the sentence text

Return only the sentence, nothing else.
```

**Output sanitization** (defense in depth — LLMs occasionally violate rule 7):

```python
import re

_DIVIDER_RE = re.compile(r"^\s*[\*\-_=]{3,}\s*$")
_ASTERISK_RE = re.compile(r"\*+")
_WS_RE = re.compile(r"\s+")

def sanitize_sentence(raw: str) -> str:
    blocks, cur = [], []
    for line in (raw or "").splitlines():
        if _DIVIDER_RE.match(line):
            if cur: blocks.append(" ".join(cur).strip()); cur = []
            continue
        line = line.strip()
        if not line:
            if cur: blocks.append(" ".join(cur).strip()); cur = []
            continue
        cur.append(line)
    if cur: blocks.append(" ".join(cur).strip())
    if not blocks: return ""
    s = _ASTERISK_RE.sub("", blocks[0])
    return _WS_RE.sub(" ", s).strip()
```

Persist the *cleaned* sentence as `text` in the manifest — that way the manifest matches what the audio actually says.

**LLM call sketch** (OpenAI-compatible; works against `https://integrate.api.nvidia.com/v1` with `NVIDIA_API_KEY` or any local NIM):

```python
import requests

def gen_sentence(term: str, entity_category: str, context_type: str,
                 api_key: str,
                 endpoint: str = "https://integrate.api.nvidia.com/v1",
                 model: str = "nvidia/nemotron-mini-4b-instruct") -> str:
    """Caller passes api_key explicitly — see the caller wires-the-credential
    note below."""
    prompt = SENTENCE_PROMPT.format(
        term=term, entity_category=entity_category, context_type=context_type,
    )
    r = requests.post(
        f"{endpoint}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 100,
        },
        timeout=30,
    )
    r.raise_for_status()
    return sanitize_sentence(r.json()["choices"][0]["message"]["content"])
```

Generate 3–5 `context_type` variants per term. Initial `context_type` vocabulary: `dictation`, `instruction`, `narrative`, `history`.

**Caller wires the credential.** `gen_sentence()` (and `magpie_synthesize()` below) take `api_key` as an explicit parameter rather than reading env vars themselves. In your driver script, fetch `NVIDIA_API_KEY` from the shell using whatever pattern your codebase prefers — a direct env-var lookup with a graceful fallback, a config-loader helper, or a secrets manager — and pass the resulting string into each recipe call.

**Template fallback** (no LLM, mechanical interpolation — Plan B for offline use):

```python
TEMPLATES = {
    "dictation":   "Patient was prescribed {term} as part of the clinical plan.",
    "instruction": "Please administer {term} according to the protocol.",
    "narrative":   "The team discussed {term} during the morning rounds.",
    "history":     "Prior history includes treatment with {term}.",
}
def fallback_sentence(term, context_type):
    return TEMPLATES[context_type].format(term=term)
```

The template path is brittle (sentences sound canned) but lets the rest of the cycle proceed when an LLM isn't reachable. Tag those rows in the manifest (e.g. set `context_type` but leave a `sentence_source=template` field) so a future cycle can regenerate.

### 2c. Two-tier IPA tagging (the load-bearing quality lever)

Every term passes through a 3-tier pipeline, in order:

1. **Override** — `pronunciation_overrides.csv` carries verified IPA the team has audited. If `term` matches a row here, the override wins.
2. **Merriam-Webster** — for un-overridden terms, fetch the MW respelling, convert to IPA, validate against Magpie's en-US phoneme set. If both succeed, the term is tagged `merriam-webster`.
3. **Magpie G2P (fall-through)** — if neither override nor MW produces a valid IPA, the plain text is passed to Magpie's neural G2P at synthesis time. The row is tagged `magpie_g2p`.

Every manifest row carries the `ipa_source` tag (`override | merriam-webster | magpie_g2p`). The delta between `merriam-webster` and `magpie_g2p` rows in the Stage 3 leaderboard **is the proof** the pronunciation strategy is working — call it out explicitly when you produce the leaderboard.

`pronunciation_overrides.csv` schema:

```csv
term,ipa,verified_by,verified_at,notes
cefazolin,sɛfəˈzoʊlɪn,brandoing,2026-05-13,confirmed against MW respelling + ear test
```

Append-only across cycles. Re-running the build later picks up new entries automatically.

**SSML wrapping** (consumed by the TTS recipe in Step 2e):

| Pronunciation kind | SSML wrap |
|---|---|
| True IPA (non-ASCII, in Magpie en-US set) | `<phoneme alphabet="ipa" ph="…">term</phoneme>` |
| Plain ASCII hint (e.g. `oh-ZEM-pick`) | `<sub alias="oh ZEM pick">term</sub>` |
| MW respelling with macron vowels (`ō`, `ā`, …) — *not* valid IPA | plain `<speak>text</speak>` — let Magpie's neural G2P handle it |
| No pronunciation hint | plain `<speak>text</speak>` |

**Multi-word terms.** Split IPA on whitespace, emit one `<phoneme>` tag per word, join back with spaces:

```python
# term = "Femoral neck", ipa = "ˈfɛ.mə.ɹəl ˈnɛk"
# → <phoneme alphabet="ipa" ph="ˈfɛ.mə.ɹəl">Femoral</phoneme> <phoneme alphabet="ipa" ph="ˈnɛk">neck</phoneme>
```

If the term has multiple words but IPA has a different word count, fall through to plain text — a malformed `<phoneme>` span breaks Magpie's parser silently.

### 2d. QA-mode synthesis (do **not** skip this gate)

Before running the full Cartesian product, synthesize **one wav per term** with: first voice, clean noise, default context. Audition each clip with the user.

For every term tagged `magpie_g2p`, propose an IPA candidate using clinical suffix patterns and validate against Magpie's en-US phoneme set **before** suggesting:

| Suffix | Stress pattern (example) |
|---|---|
| `-mycin` | …ˈmaɪsɪn (vancomycin, gentamicin) |
| `-prazole` | …ˈpreɪzoʊl (esomeprazole, omeprazole) |
| `-statin` | …ˈstætɪn (atorvastatin, rosuvastatin) |
| `-sartan` | …ˈsɑːrtən (losartan, valsartan) |
| `-azole` | …ˈeɪzoʊl (fluconazole, ketoconazole) |
| `-cillin` | …ˈsɪlɪn (amoxicillin, piperacillin) |
| `-parin` | …ˈpɛərɪn (enoxaparin, heparin) |

On user approval, append the verified IPA to `pronunciation_overrides.csv`. The row's `ipa_source` flips from `magpie_g2p` to `override` on the next manifest generation.

**Approval gate before Step 2e.** Do not synthesize the full Cartesian product until the user has explicitly approved the IPA overrides. Magpie NVCF rate-limits aggressively on >100-row jobs, and a do-over costs both API credits and clock time.

### 2e. Full benchmark generation — Magpie TTS NVCF recipe

After pronunciations are locked, generate the full Cartesian product:

```
manifest rows = |terms| × |voices| × |noise_levels| × |context_types|
```

**Common defaults:**

- **Voices** (Magpie multilingual): `Magpie-Multilingual.EN-US.Mia`, `…Jason`, `…Ray`
- **Noise levels**: `[clean, snr_15db, snr_5db]`
- **Context types**: `[dictation, instruction, narrative, history]`

**Magpie TTS NVCF recipe** (this is the load-bearing call — it replaces what `/read-aloud` would do):

```python
import io, os, random, time, wave
import riva.client

_NVCF_TTS_SERVER = "grpc.nvcf.nvidia.com:443"
_NVCF_TTS_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"  # magpie-tts-multilingual

def magpie_synthesize(ssml: str, api_key: str,
                      voice_id: str = "Magpie-Multilingual.EN-US.Mia",
                      fallback_text: str | None = None,
                      sample_rate_hz: int = 44100) -> bytes:
    """Synthesize via hosted Magpie. Returns WAV bytes.

    Caller passes api_key explicitly — read it from your own config or env."""
    lang, region = voice_id.split(".")[-1].split("-", 1)
    language_code = f"{lang.lower()}-{region.upper()}"  # "en-US"

    auth = riva.client.Auth(
        uri=_NVCF_TTS_SERVER, use_ssl=True,
        metadata_args=[
            ["function-id", _NVCF_TTS_FUNCTION_ID],
            ["authorization", f"Bearer {api_key}"],
        ],
    )
    tts = riva.client.SpeechSynthesisService(auth)

    def _run(payload: str) -> bytes:
        # Exponential backoff with jitter for RESOURCE_EXHAUSTED (hosted rate limit).
        for attempt in range(6):
            try:
                resp = tts.synthesize(
                    text=payload, voice_name=voice_id,
                    language_code=language_code,
                    encoding=riva.client.AudioEncoding.LINEAR_PCM,
                    sample_rate_hz=sample_rate_hz,
                )
                return resp.audio  # raw LINEAR_PCM bytes
            except Exception as e:
                msg = str(e)
                if not ("RESOURCE_EXHAUSTED" in msg or "rate limit" in msg) or attempt == 5:
                    raise
                time.sleep(min(2 ** attempt, 30) + random.uniform(0, 1))
        raise RuntimeError("unreachable")

    try:
        pcm = _run(ssml)
    except Exception:
        # SSML rejected? Retry with plain text once.
        if fallback_text and fallback_text != ssml:
            pcm = _run(fallback_text)
        else:
            raise

    # Wrap raw PCM in a WAV container.
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate_hz)
        w.writeframes(pcm)
    return buf.getvalue()
```

**Noise injection** (post-synthesis, additive white Gaussian noise at the specified SNR):

```python
import numpy as np, soundfile as sf

def add_noise(wav_path_in: str, wav_path_out: str, snr_db: float):
    audio, sr = sf.read(wav_path_in)
    sig_power = (audio ** 2).mean()
    noise_power = sig_power / (10 ** (snr_db / 10))
    noise = np.random.normal(0, np.sqrt(noise_power), audio.shape).astype(audio.dtype)
    sf.write(wav_path_out, audio + noise, sr)
```

Common SNR values: `snr_15db` (low noise, busy office), `snr_5db` (high noise, ICU floor). `clean` skips the noise step.

**Slug + manifest row writing:**

```python
import json, re
_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")
def slug(s: str) -> str:
    return _SLUG_RE.sub("_", s).strip("_").lower()

def write_manifest_row(out_path: str, row: dict):
    with open(out_path, "a") as f:
        f.write(json.dumps(row) + "\n")
```

**Warn when product > 100 rows.** Magpie NVCF rate-limits with ~5–10% drops on large jobs even with the backoff above. Plan a second pass to fill the gaps.

**Manifest schema** (NeMo canonical + clinical extension) is in `references/manifest-schema.md`. Both pre-flight checks (schema + audio existence) live there.

## Example scenarios

**Scenario A — fresh oncology benchmark.** User: *"We're seeing chemo drug names mistranscribed. Where do I start?"* → Step 2a: confirm specialty is oncology, ask about which drugs. Propose ~10 candidates: `cisplatin`, `paclitaxel`, `pembrolizumab`, `nivolumab`, `carboplatin`, `docetaxel`, `bevacizumab`, `trastuzumab`, `cetuximab`, `pemetrexed`. Write `term_seed.csv` with all `entity_category=drug`. Step 2b: generate 4 context variants each (40 sentences) via the inlined LLM recipe. Step 2c: MW lookup for each — biologics like `pembrolizumab` will likely fall to `magpie_g2p`; platinum agents will likely hit MW. Step 2d: synthesize one QA wav per term, walk the user through the `pembrolizumab` etc. clips, propose IPA candidates with `-mab` suffix stress patterns. Step 2e: on approval, run the Cartesian product (10 × 2 × 2 × 3 = 120 rows).

**Scenario B — appending to an existing cycle.** User: *"I have a cycle-1 manifest and I want to add 5 more procedures."* → Re-run only Steps 2a (interview for the new terms), 2b (sentence gen), 2c (IPA), 2d (audition), 2e (synthesize only the new rows). Append to the existing `manifest.jsonl`. **Do not regenerate audio for existing terms** — cycle isolation is intentional so leaderboards diff cycle N vs cycle N+1 cleanly.

## Artifacts produced

- `term_seed.csv` — curated terms with `entity_category`
- `pronunciation_overrides.csv` — verified IPA, **appendable across cycles**
- `manifest.jsonl` — NeMo format with clinical extension fields (one JSON object per line)
- `audio/<slug>.wav` — synthesized clips, one per manifest row

## Troubleshooting

- **TTS rate-limit drops (`RESOURCE_EXHAUSTED`)** on >100-row generation → the exponential backoff in the recipe handles individual calls but persistent drops indicate you're past the NVCF quota for the window. Wait ~10 minutes and re-run for the gaps.
- **All `ipa_source` rows tagged `magpie_g2p`** → MW lookup is failing across the board, or every candidate IPA is failing phoneme validation. Verify candidate IPAs against the Magpie en-US phoneme inventory before assuming they'll be accepted.
- **Magpie mispronounces a term even with the IPA override** → first verify the IPA is in the Magpie en-US phoneme inventory and the SSML wrapping is syntactically valid. If both check out and the term is multi-word, confirm the IPA word count matches the term word count (otherwise the recipe falls through to plain text). Persistent mispronunciation of a specific term despite a verified IPA is a Magpie bug — file against the Riva team (`#riva-public`).
- **Sentence variants from the LLM are bland / template-like** → check the prompt; the schema-only call sometimes produces stereotyped output. Add 1–2 in-context examples to the prompt and re-run. Or raise `temperature` to 0.6.
- **`grpc.RpcError: UNAUTHENTICATED`** → `NVIDIA_API_KEY` is missing or wrong in the shell. The length-only check in `/clinical-asr-setup` covers this.
- **Audio files exist but `manifest.jsonl` is short** → manifest writer skipped rows whose synthesis returned an NVCF error and didn't get caught by the SSML→plain-text fallback. Re-run with only the missing rows.
- **`<phoneme>` SSML is silently ignored** → Magpie's IPA parser is strict; characters outside its en-US inventory cause the tag to drop. Verify against the inventory before emitting.

## Limitations

- **English-only by default.** Magpie's en-US phoneme inventory is what the two-tier IPA pipeline validates against. Other locales need a different upstream phoneme set + override CSV format.
- **Six fixed entity categories.** Extending `entity_category` is a deliberate methodology change, not a one-off tweak — KER breakdowns, leaderboard sections, and downstream finetune scripts all key off the vocabulary.
- **Tiny first cycles.** Below ~20 terms, the by-`ipa_source` leaderboard split won't have enough rows in each bucket to be statistically meaningful. Build a meaningful cycle even if it costs a session.
- **Magpie NVCF rate-limits.** ~5–10% drops on large jobs; budget a re-run pass.

## Companion software

The runnable scripts that implement this stage live in the **`voice-eval-flywheel`** repo (`scripts/generate_eval_set.py` drives the full pipeline; `pronunciation_overrides.csv` ships with a curated starter set). You **do not need** the repo to complete this stage — every recipe needed is inlined above.

## Next steps

- **Forward:** `/clinical-asr-eval` — transcribe the manifest, score WER/CER/KER/SER, produce the five-section leaderboard.
- **Back to setup** (if anything in the env is broken): `/clinical-asr-setup`.

## References

- [`references/manifest-schema.md`](references/manifest-schema.md) — NeMo canonical fields + clinical extension; pre-flight schema and audio-existence checks; cross-cycle stability rules
