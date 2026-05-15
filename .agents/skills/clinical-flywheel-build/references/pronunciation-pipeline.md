# Pronunciation Pipeline Reference

Full Merriam-Webster respelling → IPA mapping table and SSML wrapping rules for the `clinical-flywheel-build` two-tier IPA pipeline.

## MW respelling glyph → IPA mapping

The Merriam-Webster Medical Dictionary API returns pronunciation in a respelling notation (e.g. `se-fə-ˈzō-lən`). This table maps each respelling glyph to its IPA equivalent.

### Consonants

| MW glyph | IPA | Example |
|----------|-----|---------|
| `b` | `b` | `bə(r)` → `bər` |
| `ch` | `tʃ` | `chīld` → `tʃaɪld` |
| `d` | `d` | `did` → `dɪd` |
| `f` | `f` | `fīn` → `faɪn` |
| `g` | `ɡ` | `gō` → `ɡoʊ` |
| `h` | `h` | `hat` → `hæt` |
| `j` | `dʒ` | `jest` → `dʒɛst` |
| `k` | `k` | `kit` → `kɪt` |
| `l` | `l` | `lay` → `leɪ` |
| `m` | `m` | `met` → `mɛt` |
| `n` | `n` | `not` → `nɑt` |
| `ng` | `ŋ` | `siŋ` → `sɪŋ` |
| `p` | `p` | `pet` → `pɛt` |
| `r` | `r` | `red` → `rɛd` |
| `s` | `s` | `sat` → `sæt` |
| `sh` | `ʃ` | `shōt` → `ʃoʊt` |
| `t` | `t` | `top` → `tɑp` |
| `th` | `θ` | `thin` → `θɪn` |
| `t͟h` | `ð` | `t͟his` → `ðɪs` |
| `v` | `v` | `vēn` → `viːn` |
| `w` | `w` | `wet` → `wɛt` |
| `y` | `j` | `yes` → `jɛs` |
| `z` | `z` | `zip` → `zɪp` |
| `zh` | `ʒ` | `vizhən` → `vɪʒən` |

### Vowels (stressed/unstressed)

| MW glyph | IPA | Example |
|----------|-----|---------|
| `ə` | `ə` | `sofa` → `soʊfə` (schwa) |
| `ər` | `ər` | `bird` → `bərd` |
| `a` | `æ` | `cat` → `kæt` |
| `ā` | `eɪ` | `day` → `deɪ` |
| `ä` | `ɑː` | `cot` → `kɑːt` |
| `e` | `ɛ` | `bet` → `bɛt` |
| `ē` | `iː` | `bee` → `biː` |
| `i` | `ɪ` | `sit` → `sɪt` |
| `ī` | `aɪ` | `bite` → `baɪt` |
| `o` | `ɑ` | `cot` → `kɑt` (US) |
| `ō` | `oʊ` | `boat` → `boʊt` |
| `ȯ` | `ɔ` | `caught` → `kɔt` |
| `ȯi` | `ɔɪ` | `boy` → `bɔɪ` |
| `u` | `ʌ` | `cut` → `kʌt` |
| `u̇` | `ʊ` | `book` → `bʊk` |
| `ü` | `uː` | `boot` → `buːt` |
| `aü` | `aʊ` | `out` → `aʊt` |
| `yü` | `juː` | `cute` → `kjuːt` |

### Stress and syllabification

| MW glyph | IPA | Meaning |
|----------|-----|---------|
| `ˈ` | `ˈ` | Primary stress (precedes stressed syllable) |
| `ˌ` | `ˌ` | Secondary stress |
| `-` | (drop) | Syllable boundary — drop before mapping |
| `(ˌ)` | (drop) | Optional secondary stress — drop |

## Walk-through example

MW respelling for **cefazolin**: `se-fə-ˈzō-lən`

1. Strip `-`: `sefəˈzōlən`
2. Apply table left-to-right (longest match first):
   - `s` → `s`
   - `e` → `ɛ`
   - `f` → `f`
   - `ə` → `ə`
   - `ˈ` → `ˈ`
   - `z` → `z`
   - `ō` → `oʊ`
   - `l` → `l`
   - `ə` → `ə`
   - `n` → `n`
3. Result: `sɛfəˈzoʊlən`

## SSML wrapping rules

When `ipa_source` is `override` or `merriam-webster`, wrap the term in SSML so Magpie applies the IPA hint instead of relying on its neural G2P:

```python
import re

def wrap_with_ipa(term: str, ipa: str) -> str:
    """Single-token SSML wrap."""
    return f'<phoneme alphabet="ipa" ph="{ipa}">{term}</phoneme>'

def wrap_multiword(term: str, ipa: str) -> str:
    """Multi-token wrap. <sub alias> gives Magpie a text fallback if it can't
    handle the IPA; the inner <phoneme> is the preferred path."""
    return f'<sub alias="{ipa}"><phoneme alphabet="ipa" ph="{ipa}">{term}</phoneme></sub>'

def render_sentence_with_overrides(sentence: str, overrides: dict[str, str]) -> str:
    """Replace each overridden term in `sentence` with its SSML wrap.
    Matches whole words only to avoid wrapping substrings."""
    for term, ipa in overrides.items():
        wrap = wrap_with_ipa(term, ipa) if " " not in term else wrap_multiword(term, ipa)
        sentence = re.sub(rf'\b{re.escape(term)}\b', wrap, sentence)
    return sentence
```

### Edge cases

- **Punctuation adjacent to the term** (`cefazolin,`): `\b` boundary handles this naturally — the comma stays outside the wrap.
- **Term that contains hyphens** (`auto-immune`): re-escape the hyphen; the wrap still produces valid SSML.
- **IPA that contains quotes**: shouldn't occur with the MW mapping above, but if a hand-curated override does, replace `"` with `&quot;` inside the SSML attribute.
- **Capitalized term in mid-sentence** (`Cefazolin`): use `re.IGNORECASE` if you want case-insensitive matching, but preserve the original casing in the wrap's display text.

## Notes

- MW Medical Dictionary's free tier is 1000 queries/day with a registered API key. Cache successful lookups in `pronunciation_overrides.csv` so re-runs of the build pipeline don't re-query.
- Coverage: MW Medical Dictionary covers most generic drug names, anatomy, and common procedures. Long-tail biologics (`-mab` antibodies, `-mab` checkpoint inhibitors) often miss; those fall through to `magpie_g2p`.
- The mapping table above is sufficient for ~95% of clinical respellings. If a respelling contains a glyph not in the table, the `_respelling_to_ipa` function passes it through unchanged, which will fail Magpie phoneme validation downstream — surface that as a candidate for hand-curation in `pronunciation_overrides.csv`.
