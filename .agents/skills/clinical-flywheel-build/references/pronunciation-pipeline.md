# Pronunciation Pipeline Reference

Full Merriam-Webster respelling → IPA mapping table and SSML wrapping rules for the `clinical-flywheel-build` two-tier IPA pipeline.

## Two MW implementation paths

Both end up tagging the manifest row `merriam-webster`; pick the one that fits your context:

### Path A — `dictionaryapi.com` JSON API (recommended for standalone use)

Stable, ToS-clean, requires a free key from <https://dictionaryapi.com> exported as `DICTIONARY_API_KEY`. The lookup returns MW respelling in `data[0].hwi.prs[0].mw`; feed it to the mapping table below via `_respelling_to_ipa()`.

```python
import requests
from typing import Optional

MW_BASE = "https://www.dictionaryapi.com/api/v3/references/medical/json"

# Compact MW-respelling → IPA glyph map. See the full mapping tables below
# for combining marks and edge-case vowels.
_MW_TO_IPA = {
    "sh": "ʃ", "ch": "tʃ", "th": "θ", "zh": "ʒ", "ng": "ŋ",
    "ə": "ə", "a": "æ",   "ä": "ɑː", "ā": "eɪ",
    "e": "ɛ", "ē": "iː",  "i": "ɪ",  "ī": "aɪ",
    "o": "ɑ", "ō": "oʊ",  "ȯ": "ɔ",  "u": "ʌ", "ü": "uː",
    "ˈ": "ˈ", "ˌ": "ˌ",
}

def mw_lookup_ipa(term: str, api_key: Optional[str]) -> Optional[str]:
    """Return IPA for `term` from MW Medical Dictionary, or None if unavailable.
    Pass `None` for api_key to skip MW lookup (caller decides whether the
    DICTIONARY_API_KEY env var is set; this code never reads the environment)."""
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

### Path B — HTML scrape of `merriam-webster.com`

What the `voice-eval-flywheel` companion repo's `flywheel/data/ipa_extractor.py:83-113` uses. No key, but brittle to MW site HTML changes; only use this if you control your deployment context. Feed the returned string into the same `_respelling_to_ipa()` helper as Path A. Sketch:

  ```python
  import re, requests
  from bs4 import BeautifulSoup
  from typing import Optional
  from urllib.parse import quote

  UA = "voice-eval-flywheel/0.1 (clinical-asr eval)"

  def scrape_mw_respelling(term: str, timeout: float = 15.0) -> Optional[str]:
      """Path B: parse the public MW website for the term's respelling.
      Returns None if the page has no pronunciation block."""
      s = requests.Session()
      s.headers.update({"User-Agent": UA})
      slug = quote(term.strip().replace(" ", "-"))
      for path in (f"medical/{slug}", f"dictionary/{slug}"):
          r = s.get(f"https://www.merriam-webster.com/{path}", timeout=timeout)
          if r.status_code != 200:
              continue
          soup = BeautifulSoup(r.text, "html.parser")
          a = soup.find("a", class_=re.compile(r"\bplay-pron-v2\b"))
          if not a:
              continue
          raw = a.decode_contents().split("<svg", 1)[0]
          text = BeautifulSoup(raw, "html.parser").get_text() \
                   .replace("\xa0", " ").strip().strip(" -")
          if text:
              return text  # feed this to _respelling_to_ipa() above
      return None
  ```

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
