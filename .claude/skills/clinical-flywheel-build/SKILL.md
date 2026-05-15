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
  companion_software: "voice-eval-flywheel (optional)"
  previous_skill: clinical-flywheel-setup
  next_skill: clinical-flywheel-eval
---

# Clinical ASR Flywheel — Stage 2 (Build the benchmark)

You are the **curate-and-synthesize** stage. The user arrives from `/clinical-flywheel-setup` and leaves with a NeMo-format `manifest.jsonl` plus the audio it references — both ready for scoring at `/clinical-flywheel-eval`.

Be conversational. This is the warmest, most domain-aware step in the flywheel: you're asking a clinician (or someone who works with them) which terms hurt today and shaping a benchmark around their reality. Ask short, focused questions. Show the user what's being added. Don't lecture.

## ⚠️ Data leaves your environment — disclose this to the user before any term is sent

This stage transmits user-curated content to two external services. Surface this to the user before invoking either call:

| Service | What gets sent | When |
|---|---|---|
| **Merriam-Webster Medical Dictionary** (`dictionaryapi.com`) | One HTTP request per clinical term in the seed list — the term string itself goes in the URL path | Step 2c, **only if** `DICTIONARY_API_KEY` is set |
| **NVIDIA NVCF Magpie TTS** (`grpc.nvcf.nvidia.com`) | Each generated clinical sentence (text, plus any SSML IPA wrappers) | Steps 2d and 2e, every synthesis call |

Both endpoints expect **non-PHI synthetic content** — the term list you curate, the sentences `/data-designer` (or your fallback templates) generates from it. **Do not pass real patient records, real ASR transcripts, or any PHI through this skill.** If the term list itself is sensitive (proprietary drug codenames, unreleased product names, customer-confidential indications), confirm with the user that external-API transmission is acceptable under their organization's data-governance policy before proceeding.

If MW transmission is not acceptable: leave `DICTIONARY_API_KEY` unset. The IPA pipeline falls through to Magpie G2P and the workflow still produces a valid benchmark.

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

(`$EVAL_DIR` is the user's own choice — this skill does not impose a layout. The structure above is a recommendation that works well with the companion software when the user later opts into it.)

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

The output of this step is a per-term sentence variants file. The companion software writes it as `term_seed_with_sentences.csv`; skill-only users can use any name.

**Template fallback.** If `/data-designer` is unavailable, use a 4-template fallback (one per `context_type`) and substitute `term` mechanically. Tag those rows in the manifest (`context_type` is set, the sentence is just less natural) so a future cycle can regenerate.

### 2c. Two-tier IPA tagging (the load-bearing quality lever)

Every term passes through a 3-tier pipeline, in order:

1. **Override** — `pronunciation_overrides.csv` carries verified IPA the team has audited. If `term` matches a row here, the override wins.
2. **Merriam-Webster** — for un-overridden terms, fetch the MW respelling, convert to IPA, validate against Magpie's en-US phoneme set. If both succeed, the term is tagged `merriam-webster`.
3. **Magpie G2P (fall-through)** — if neither override nor MW produces a valid IPA, the plain text is passed to Magpie's neural G2P at synthesis time. The row is tagged `magpie_g2p`.

Every manifest row carries the `ipa_source` tag (`override | merriam-webster | magpie_g2p`). The delta between `merriam-webster` and `magpie_g2p` rows in the Stage 3 leaderboard **is the proof** the pronunciation strategy is working — call it out explicitly when you produce the leaderboard.

**Inline MW lookup recipe** (self-contained, no sibling skill required). Requires `DICTIONARY_API_KEY` env var (free tier at <https://dictionaryapi.com>). If unset, return `None` and let the pipeline fall through to `magpie_g2p` — this is correct behavior, not an error.

```python
import os, requests

MW_BASE = "https://www.dictionaryapi.com/api/v3/references/medical/json"
MW_API_KEY_VAR = "DICTIONARY_API_KEY"

# Compact MW-respelling → IPA glyph map. See references/pronunciation-pipeline.md
# for the complete table covering combining marks and edge-case vowels.
_MW_TO_IPA = {
    "sh": "ʃ", "ch": "tʃ", "th": "θ", "zh": "ʒ", "ng": "ŋ",
    "ə": "ə", "a": "æ",   "ä": "ɑː", "ā": "eɪ",
    "e": "ɛ", "ē": "iː",  "i": "ɪ",  "ī": "aɪ",
    "o": "ɑ", "ō": "oʊ",  "ȯ": "ɔ",  "u": "ʌ", "ü": "uː",
    "ˈ": "ˈ", "ˌ": "ˌ",
}

def mw_lookup_ipa(term: str) -> str | None:
    """Return IPA for `term` from MW Medical Dictionary, or None if unavailable."""
    api_key = os.environ.get(MW_API_KEY_VAR)
    if not api_key:
        return None
    r = requests.get(f"{MW_BASE}/{term}", params={"key": api_key}, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data or not isinstance(data[0], dict):
        return None  # MW returned spelling suggestions, not an entry
    prs = data[0].get("hwi", {}).get("prs", [])
    if not prs or "mw" not in prs[0]:
        return None
    return _respelling_to_ipa(prs[0]["mw"])

def _respelling_to_ipa(respelling: str) -> str:
    """MW respelling → IPA. Digraphs (sh, ch, th, zh, ng) match before single chars.
    Syllable dots are dropped; stress marks are preserved."""
    s = respelling.replace("-", "")
    out, i = [], 0
    while i < len(s):
        if i + 1 < len(s) and s[i:i+2] in _MW_TO_IPA:
            out.append(_MW_TO_IPA[s[i:i+2]]); i += 2; continue
        out.append(_MW_TO_IPA.get(s[i], s[i])); i += 1
    return "".join(out)
```

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

**Approval gate before Step 2e.** Do not synthesize the full Cartesian product until the user has explicitly approved the IPA overrides. Magpie NVCF rate-limits aggressively on >100-row jobs, and a do-over costs both API credits and clock time.

### 2e. Full benchmark generation

After pronunciations are locked, generate the full **Cartesian product**:

```
manifest rows = |terms| × |voices| × |noise_levels| × |context_types|
```

Common defaults:

- **Voices**: 2–4 Magpie en-US voices (e.g. `Magpie-Multilingual.EN-US.Mia`, `Jason`, `Ray`)
- **Noise levels**: `[clean, snr_15db, snr_5db]`
- **Context types**: `[dictation, handoff, chart_note, history]`

**Self-contained synthesis path** (no `/read-aloud` skill required). Reuse the `riva.client` SDK set up in `/clinical-flywheel-setup`:

```python
import re, json, os
from pathlib import Path
import riva.client

NVCF_HOST = "grpc.nvcf.nvidia.com:443"
MAGPIE_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"

def wrap_with_ipa(term: str, ipa: str) -> str:
    """Single-token SSML phoneme wrap. Use wrap_multiword() for terms with spaces."""
    if " " in term:
        return f'<sub alias="{ipa}"><phoneme alphabet="ipa" ph="{ipa}">{term}</phoneme></sub>'
    return f'<phoneme alphabet="ipa" ph="{ipa}">{term}</phoneme>'

def render_with_overrides(sentence: str, term: str, ipa: str | None) -> str:
    """Replace `term` in `sentence` with its SSML wrap when ipa is provided."""
    if not ipa:
        return sentence
    return re.sub(rf'\b{re.escape(term)}\b', wrap_with_ipa(term, ipa), sentence)

def synthesize_row(row: dict, out_dir: Path, api_key: str) -> Path:
    """Synthesize one manifest row to <out_dir>/audio/<slug>.wav. Returns the path."""
    auth = riva.client.Auth(
        ssl_cert=None, use_ssl=True, uri=NVCF_HOST,
        metadata_args=[
            ["function-id", MAGPIE_FUNCTION_ID],
            ["authorization", f"Bearer {api_key}"],
        ],
    )
    tts = riva.client.SpeechSynthesisService(auth)
    text = row["text"]
    if row["ipa_source"] in ("override", "merriam-webster"):
        text = f"<speak>{render_with_overrides(text, row['term'], row['ipa'])}</speak>"
    slug = f"{row['term']}_{row['context_type']}_{row['voice_id']}_{row['noise_level']}"
    slug = re.sub(r'[^a-z0-9]+', '_', slug.lower())
    audio_path = out_dir / "audio" / f"{slug}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    pcm = b"".join(c.audio for c in tts.synthesize_online(
        text=text, voice_name=row["voice_id"],
        language_code="en-US", sample_rate_hz=16000,
    ))
    # PCM → WAV (16-bit mono, 16 kHz).
    import wave
    with wave.open(str(audio_path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(pcm)
    return audio_path
```

For the noise-injection step (clean → snr_15db → snr_5db variants), see `references/manifest-schema.md` for the SNR-mixing formula. Apply it after synthesis to the clean WAV.

Full SSML wrapping rules (multi-word terms, punctuation edge cases, fallback rendering) live in `references/pronunciation-pipeline.md`.

**Warn when product > 100 rows.** Magpie NVCF rate-limits with ~5–10% `RESOURCE_EXHAUSTED` drops on big runs. Exponential backoff in `/read-aloud` handles most, but expect a re-run pass for the gaps.

**Manifest schema** (NeMo canonical + clinical extension) is in `references/manifest-schema.md`. Both pre-flight checks (schema + audio existence) live there.

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
- **All `ipa_source` rows tagged `magpie_g2p`** → MW lookup is failing across the board, or every candidate IPA is failing phoneme validation. Check `MW_API_KEY` env var (if your `/read-aloud` flow uses MW); verify candidate IPAs against the Magpie en-US phoneme inventory before assuming they'll be accepted.
- **Magpie mispronounces a term even with the IPA override** → first verify the IPA is in the Magpie en-US phoneme inventory and the SSML wrapping is syntactically valid. If both check out, the underlying TTS bug is owned by `/read-aloud` (`/riva-tts`) — route there for diagnosis. This skill provides the override mechanism but does not own the neural G2P or SSML parser.
- **Sentence variants from `/data-designer` are bland / template-like** → check the brief; the schema-only prompt sometimes produces stereotyped output. Add 1–2 in-context examples to the brief and re-run.
- **Audio files exist but `manifest.jsonl` is short** → manifest writer skipped rows whose synthesis returned a NVCF error. Re-run the build with only the missing rows.

For anything not in this list, identify which upstream skill is implicated and route there. The `clinical-flywheel-build` skill owns the methodology, not the TTS or DataDesigner internals.

## Limitations

- **English-only by default.** Magpie's en-US phoneme inventory is what the two-tier IPA pipeline validates against. Other locales need a different upstream phoneme set + override CSV format.
- **Six fixed entity categories.** Extending `entity_category` is a deliberate methodology change, not a one-off tweak — KER breakdowns, leaderboard sections, and downstream finetune scripts all key off the vocabulary.
- **Tiny first cycles.** Below ~20 terms, the by-`ipa_source` leaderboard split won't have enough rows in each bucket to be statistically meaningful. Build a meaningful cycle even if it costs a session.
- **Magpie NVCF rate-limits.** ~5–10% drops on large jobs; budget a re-run pass.

## Companion software

Runnable scripts that implement this stage live in the (currently internal) **`voice-eval-flywheel`** repo: `scripts/generate_eval_set.py` drives DataDesigner + Magpie end-to-end with retry logic; `pronunciation_overrides.csv` ships with a curated starter set; `config/eval.yaml` carries an opinionated cycle layout. You **do not need** the repo to complete this stage — composing `/data-designer` + `/read-aloud` with the recipes above is sufficient.

## Next steps

- **Forward:** `/clinical-flywheel-eval` — transcribe the manifest, score WER/CER/KER/SER, produce the five-section leaderboard.
- **Back to setup** (if anything in the env is broken): `/clinical-flywheel-setup`.
- **Lateral** for TTS-specific debugging: `/read-aloud` or `/riva-tts`.

## References

- [`references/manifest-schema.md`](references/manifest-schema.md) — NeMo canonical fields + clinical extension; pre-flight schema and audio-existence checks; cross-cycle stability rules
