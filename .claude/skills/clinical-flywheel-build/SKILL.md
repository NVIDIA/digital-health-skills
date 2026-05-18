---
name: "clinical-flywheel-build"
description: "Stage 2 of the Clinical ASR Flywheel. Use when curating clinical terms, tagging IPA, and synthesizing a NeMo manifest. NOT for scoring (use /clinical-flywheel-eval)."
version: "1.1.0"
author: "Ben Randoing <brandoing@nvidia.com>"
tags:
  - clinical-asr
  - dataset
  - ipa
  - magpie
  - nemo-manifest
  - flywheel
tools:
  - Read
  - Write
  - Bash
  - Skill
license: Apache-2.0
compatibility: "NVIDIA_API_KEY (required) for hosted Magpie TTS via NVCF. DICTIONARY_API_KEY (optional) for Merriam-Webster Medical Dictionary lookup. Stage 1 (/clinical-flywheel-setup) must have been completed first. All TTS, IPA, and synthesis recipes are inlined — no sibling agent skill required."
metadata:
  author: "Ben Randoing <brandoing@nvidia.com>"
  tags:
    - clinical-asr
    - flywheel
    - dataset
    - ipa
    - magpie
  team: healthcare-tme
  domain: ai-ml
  stage: 2
  previous_skill: clinical-flywheel-setup
  next_skill: clinical-flywheel-eval
---

# Clinical ASR Flywheel — Stage 2 (Build the benchmark)

You are the **curate-and-synthesize** stage. The user arrives from `/clinical-flywheel-setup` and leaves with a NeMo-format `manifest.jsonl` plus the audio it references — both ready for scoring at `/clinical-flywheel-eval`.

Be conversational. This is the warmest, most domain-aware step in the flywheel: you're asking a clinician (or someone who works with them) which terms hurt today and shaping a benchmark around their reality. Ask short, focused questions. Show the user what's being added. Don't lecture.

## Data leaves your environment — disclose this to the user before any term is sent

This stage transmits user-curated content to two external services. Surface this to the user before invoking either call:

| Service | What gets sent | When |
|---|---|---|
| **Merriam-Webster** (`dictionaryapi.com` API or `merriam-webster.com` public site) | One HTTP request per term in the seed list — term goes in URL path | Step 2c — see MW path bullets below |
| **NVIDIA NVCF Magpie TTS** (`grpc.nvcf.nvidia.com`) | Each generated clinical sentence (text, plus any SSML IPA wrappers) | Steps 2d and 2e, every synthesis call |

Both endpoints expect **non-PHI synthetic content** — the term list you curate, the sentences `/data-designer` (or your fallback templates) generates from it. **Do not pass real patient records, real ASR transcripts, or any PHI through this skill.** If the term list itself is sensitive (proprietary drug codenames, unreleased product names, customer-confidential indications), confirm with the user that external-API transmission is acceptable under their organization's data-governance policy before proceeding.

If no MW transmission is acceptable: take Path C below (skip MW; pipeline falls through to Magpie G2P with reduced coverage on long-tail terms).

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

(`$EVAL_DIR` is the user's own choice — this skill does not impose a layout. The structure above is a recommendation, not a requirement.)

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

- The user already has a manifest and wants to score it → `/clinical-flywheel-eval`
- The user wants to fine-tune on an existing manifest → `/clinical-flywheel-finetune`
- The user is asking generic TTS / SSML / voice-cloning questions → `/read-aloud` (or `/riva-tts`)
- The user is asking generic synthetic-data questions → `/data-designer`

## Prerequisites

- **`/clinical-flywheel-setup` completed** — `NVIDIA_API_KEY` exported, Python deps installed, the six upstream skills confirmed.
- **`/read-aloud`** (or `/riva-tts`) reachable. Hosted Magpie via NVCF is the default. Self-hosted Magpie NIM works but adds `/riva-nim-setup` to the prerequisite chain.
- **`/data-designer`** reachable. Template fallback is acceptable for a first cycle if `/data-designer` is unavailable, but tag those rows so future cycles can re-generate.
- **A working directory** the user owns. The skill recommends `$EVAL_DIR/cycle<N>/` but does not enforce it.

## Instructions

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

### 2b. Sentence generation via `/data-designer`

Brief `/data-designer` with:

> For each row in `term_seed.csv`, generate one or more natural English sentences embedding `term` in a way that fits the row's `entity_category`. Output schema: `{term, entity_category, sentence, context_type}`. Generate 3–5 `context_type` variants per term. Initial `context_type` vocabulary: `dictation`, `handoff`, `chart_note`, `history`. Sentence length 10–30 words.

The output of this step is a per-term sentence variants file. Any filename is fine — pick one and use it consistently across the cycle directory.

**Template fallback.** If `/data-designer` is unavailable, use a 4-template fallback (one per `context_type`) and substitute `term` mechanically. Tag those rows in the manifest (`context_type` is set, the sentence is just less natural) so a future cycle can regenerate.

### 2c. Two-tier IPA tagging (the load-bearing quality lever)

Every term passes through a 3-tier pipeline, in order:

1. **Override** — `pronunciation_overrides.csv` carries verified IPA the team has audited. If `term` matches a row here, the override wins.
2. **Merriam-Webster** — for un-overridden terms, fetch the MW respelling, convert to IPA, validate against Magpie's en-US phoneme set. If both succeed, the term is tagged `merriam-webster`.
3. **Magpie G2P (fall-through)** — if neither override nor MW produces a valid IPA, the plain text is passed to Magpie's neural G2P at synthesis time. The row is tagged `magpie_g2p`.

Every manifest row carries the `ipa_source` tag (`override | merriam-webster | magpie_g2p`). The delta between `merriam-webster` and `magpie_g2p` rows in the Stage 3 leaderboard **is the proof** the pronunciation strategy is working — call it out explicitly when you produce the leaderboard.

**Three MW lookup choices** — all tag `merriam-webster`. **A**: `dictionaryapi.com` JSON API + `DICTIONARY_API_KEY` (free at dictionaryapi.com) — recommended for standalone use. **B**: HTML scrape of `merriam-webster.com` — no key, brittle to site HTML changes; recipe inlined in `references/pronunciation-pipeline.md`. **C**: skip MW, fall through to Magpie G2P with weaker long-tail coverage. Both recipes + the full respelling→IPA table live in `references/pronunciation-pipeline.md`. The Path A function takes `api_key` as an arg (never reads `os.environ`); pass `None` to skip MW.

`pronunciation_overrides.csv` schema:

```csv
term,ipa,verified_by,verified_at,notes
cefazolin,sɛfəˈzoʊlɪn,brandoing,2026-05-13,confirmed against MW respelling + ear test
```

Append-only across cycles. Re-running the build later picks up new entries automatically.

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

**Inline phoneme-validation recipe** — live-probe Magpie's en-US neural G2P with a candidate IPA. If Magpie accepts the SSML, the IPA is in its inventory. Use the suffix patterns above as a *pre-filter* (cheap heuristic) and the live probe to confirm before committing to an override.

```python
import grpc
import riva.client  # pip install nvidia-riva-client

NVCF_HOST = "grpc.nvcf.nvidia.com:443"
MAGPIE_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"

def magpie_validates_ipa(ipa: str, api_key: str,
                         voice_id: str = "Magpie-Multilingual.EN-US.Mia") -> bool:
    """Return True if Magpie accepts the IPA via SSML <phoneme>.

    Sends a minimal synthesis request and consumes the audio stream.
    InvalidArgument (or any "phoneme" error) → False. Network/auth errors
    also return False (fail-closed)."""
    ssml = f'<speak><phoneme alphabet="ipa" ph="{ipa}">test</phoneme></speak>'
    try:
        auth = riva.client.Auth(
            ssl_cert=None, use_ssl=True, uri=NVCF_HOST,
            metadata_args=[
                ["function-id", MAGPIE_FUNCTION_ID],
                ["authorization", f"Bearer {api_key}"],
            ],
        )
        tts = riva.client.SpeechSynthesisService(auth)
        # Consume the audio stream to surface any phoneme-rejection error.
        for _chunk in tts.synthesize_online(
            text=ssml, voice_name=voice_id,
            language_code="en-US", sample_rate_hz=16000,
        ):
            pass
        return True
    except grpc.RpcError:
        return False
```

Call this once per candidate IPA before showing it to the user. On user approval, append the verified IPA to `pronunciation_overrides.csv`. The row's `ipa_source` flips from `magpie_g2p` to `override` on the next manifest generation.

**HITL audition gate before Step 2e — fail-closed.** Do not synthesize the full Cartesian product, do not promote any staged IPA candidate to `pronunciation_overrides.csv`, and do not advance to Stage 3 until **one of the following has happened explicitly in conversation**:

1. **The user confirms they have auditioned the QA clips** and reports their verdict per clip (or per bucket: "the MW set sounds fine", "fix `pembrolizumab`", etc.). Provide the `afplay` (macOS) or `paplay`/`aplay` (Linux) commands so the user can play them — then **halt and wait for their reply after listening**. Paper-only approval via an AskUserQuestion prompt — clicking "Promote all" or "Lock in" without auditioning — **does not satisfy this gate**. Magpie-validating an IPA proves it's in the phoneme inventory; it does not prove it matches the *intended* pronunciation. Only the user's ears do that.
2. **The user explicitly opts to skip audition for this cycle**, in deliberate language (e.g. *"skip audition, accept the risk that mispronunciations may dilute the Stage 3 KER signal — log it as a cycle-N caveat"*), not as a side-effect of a single click-through. Record the skip in a cycle-level note (e.g. `eval/cycle<N>/cycle_notes.md`) so a future operator can see the audition was deferred.

Magpie NVCF rate-limits aggressively on >100-row jobs, and a do-over costs both API credits and clock time — but the larger risk is shipping a manifest with mispronounced reference audio that quietly corrupts the Stage 3 KER signal. Time spent auditioning is cheaper than re-running the cycle.

### 2e. Full benchmark generation

After pronunciations are locked, generate the full Cartesian product `|terms| × |voices| × |noise_levels| × |context_types|`. Defaults: 2–4 Magpie en-US voices (Mia/Jason/Ray), `[clean, snr_15db, snr_5db]`, `[dictation, handoff, chart_note, history]`.

Self-contained synthesis (no `/read-aloud` required). SSML wrap helpers and edge-case rules live in `references/pronunciation-pipeline.md`; this block focuses on the synthesis call:

```python
import re
from pathlib import Path
import riva.client
# from .pronunciation_pipeline import render_with_overrides  # see references/

NVCF_HOST = "grpc.nvcf.nvidia.com:443"
MAGPIE_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"

def synthesize_row(row: dict, all_overrides: dict[str, str],
                   out_dir: Path, api_key: str) -> Path:
    """Synthesize one manifest row to <out_dir>/audio/<slug>.wav. Returns the path.

    `all_overrides` is a {term: ipa} dict containing *every* entry from
    `pronunciation_overrides.csv` — including context-word overrides like
    `intravenously` that are not benchmarked terms themselves. The renderer
    wraps each one whose verbatim text appears in `row['text']`.

    The row's own MW IPA (when `ipa_source=='merriam-webster'`) is merged into
    `all_overrides` for the duration of this call so MW-tagged rows still get
    their term wrapped. Manual `override` rows are already in the dict by
    construction.
    """
    auth = riva.client.Auth(
        ssl_cert=None, use_ssl=True, uri=NVCF_HOST,
        metadata_args=[
            ["function-id", MAGPIE_FUNCTION_ID],
            ["authorization", f"Bearer {api_key}"],
        ],
    )
    tts = riva.client.SpeechSynthesisService(auth)
    text = row["text"]
    overrides_for_row = dict(all_overrides)
    if row["ipa_source"] == "merriam-webster" and row.get("ipa"):
        overrides_for_row[row["term"]] = row["ipa"]
    if overrides_for_row:
        # render_sentence_with_overrides wraps EVERY override found in the
        # sentence — see references/pronunciation-pipeline.md. Wrapping only
        # row['term'] means context-word overrides are silently dropped.
        text = f"<speak>{render_sentence_with_overrides(text, overrides_for_row)}</speak>"
    slug = re.sub(r'[^a-z0-9]+', '_',
                  f"{row['term']}_{row['context_type']}_{row['voice_id']}_{row['noise_level']}".lower())
    audio_path = out_dir / "audio" / f"{slug}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    pcm = b"".join(c.audio for c in tts.synthesize_online(
        text=text, voice_name=row["voice_id"],
        language_code="en-US", sample_rate_hz=16000,
    ))
    import wave
    with wave.open(str(audio_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm)
    return audio_path
```

Noise-injection (clean → `snr_15db` → `snr_5db`) and the manifest schema (NeMo canonical fields + clinical extension, plus pre-flight schema and audio-existence checks) all live in `references/manifest-schema.md` — see the References section below for the canonical pointer.

**Warn when product > 100 rows.** Magpie NVCF rate-limits with ~5–10% `RESOURCE_EXHAUSTED` drops on big runs. Re-run the dropped rows.

### Stage 2 completion checklist

Don't consider Stage 2 done until all five sub-steps ran. Agents commonly stop after 2a or 2b; the goal is a synthesized manifest plus a hand-off:

- **2a** — `term_seed.csv`, 4–10 terms, `entity_category ∈ {drug, procedure, anatomy, condition, lab, role}`
- **2b** — 3–5 `context_type` sentence variants per term
- **2c** — every term tagged `ipa_source ∈ {override, merriam-webster, magpie_g2p}`
- **2d** — QA wavs auditioned, IPA overrides locked with explicit user approval
- **2e** — `manifest.jsonl` + per-row audio for the Cartesian product
- **Hand-off** — name `/clinical-flywheel-eval` as the next skill and **KER** as its headline metric

Writes go only into the user-chosen `$EVAL_DIR/cycle<N>/`. Don't write elsewhere, modify env, or install packages — those belong to `/clinical-flywheel-setup`.

## Examples

**Scenario A — fresh oncology benchmark.** User: *"We're seeing chemo drug names mistranscribed. Where do I start?"* → Step 2a: confirm specialty is oncology, ask about which drugs (immunotherapy biologics, platinum agents, taxanes). Propose ~10 candidates: `cisplatin`, `paclitaxel`, `pembrolizumab`, `nivolumab`, `carboplatin`, `docetaxel`, `bevacizumab`, `trastuzumab`, `cetuximab`, `pemetrexed`. Write `term_seed.csv` with all `entity_category=drug`. Step 2b: brief `/data-designer` for 4 context variants each = 40 sentences. Step 2c: MW lookup for each — biologics like `pembrolizumab` will likely fall to `magpie_g2p`; platinum agents likely hit MW. Step 2d: synthesize one QA wav per term, walk the user through the `pembrolizumab` etc. clips, propose IPA candidates with `-mab` suffix stress patterns. Step 2e: on approval, run 10 terms × 2 voices × 2 noise levels × 3 contexts = 120 rows.

**Scenario B — appending to an existing cycle.** User: *"I have a cycle-1 manifest and I want to add 5 more procedures."* → Re-run only Steps 2a (specialty interview just for the new terms), 2b (sentence gen for the additions), 2c (IPA pipeline for the additions), 2d (audition the new terms), and 2e (synthesize only the new term rows). Append to the existing `manifest.jsonl`. **Do not regenerate audio for existing terms** — cycle isolation is intentional so leaderboards diff cycle N vs cycle N+1 cleanly.

## Artifacts produced

- `term_seed.csv` — curated terms with `entity_category`
- `pronunciation_overrides.csv` — verified IPA, **appendable across cycles**
- `manifest.jsonl` — NeMo format with clinical extension fields (one JSON object per line)
- `audio/<slug>.wav` — synthesized clips, one per manifest row

## Troubleshooting

- **TTS rate-limit drops (`RESOURCE_EXHAUSTED`)** on >100-row generation → expected on Magpie NVCF. Confirm exponential backoff is active in `/read-aloud`; expect ~5–10% drops on big runs and re-run for the gaps.
- **All `ipa_source` rows tagged `magpie_g2p`** → MW lookup is failing across the board, or candidate IPAs are failing phoneme validation. Re-verify whichever MW path you configured (`DICTIONARY_API_KEY` for A; HTTPS reachability + parser for B), then check candidates against Magpie's en-US phoneme inventory.
- **Magpie mispronounces a term even with the IPA override** → first verify the IPA is in the Magpie en-US phoneme inventory and the SSML wrapping is syntactically valid. If both check out, the underlying TTS bug is owned by `/read-aloud` (`/riva-tts`) — route there for diagnosis. This skill provides the override mechanism but does not own the neural G2P or SSML parser.
- **Sentence variants from `/data-designer` are bland / template-like** → check the brief; the schema-only prompt sometimes produces stereotyped output. Add 1–2 in-context examples to the brief and re-run.
- **Audio files exist but `manifest.jsonl` is short** → manifest writer skipped rows whose synthesis returned a NVCF error. Re-run the build with only the missing rows.

For anything not in this list, identify which upstream skill is implicated and route there. The `clinical-flywheel-build` skill owns the methodology, not the TTS or DataDesigner internals.

## Limitations

- **English-only by default.** Magpie's en-US phoneme inventory is what the two-tier IPA pipeline validates against. Other locales need a different upstream phoneme set + override CSV format.
- **Six fixed entity categories.** Extending `entity_category` is a deliberate methodology change, not a one-off tweak — KER breakdowns, leaderboard sections, and downstream finetune scripts all key off the vocabulary.
- **Tiny first cycles.** Below ~20 terms, the by-`ipa_source` leaderboard split won't have enough rows in each bucket to be statistically meaningful. Build a meaningful cycle even if it costs a session.
- **Magpie NVCF rate-limits.** ~5–10% drops on large jobs; budget a re-run pass.

## Next steps

- **Forward:** `/clinical-flywheel-eval` — transcribe the manifest, score WER/CER/KER/SER, produce the five-section leaderboard.
- **Back to setup** (if anything in the env is broken): `/clinical-flywheel-setup`.
- **Lateral** for TTS-specific debugging: `/read-aloud` or `/riva-tts`.

## References

- [`references/manifest-schema.md`](references/manifest-schema.md) — NeMo canonical fields + clinical extension; pre-flight schema and audio-existence checks; cross-cycle stability rules
