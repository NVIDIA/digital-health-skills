## Description: <br>
Stage 2 of the Clinical ASR Flywheel. Use when curating clinical terms, tagging IPA, and synthesizing a NeMo manifest. NOT for scoring (use /digital-health-clinical-asr-eval). <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner: NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and clinical engineers building ASR evaluation benchmarks use this skill to curate specialty-specific clinical terms, generate IPA-tagged pronunciation data, and synthesize NeMo-format audio manifests for downstream ASR scoring. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Manifest Schema (NeMo canonical + clinical extension)](references/manifest-schema.md) <br>
- [Pronunciation Pipeline Reference](references/pronunciation-pipeline.md) <br>


## Skill Output: <br>
**Output Type(s):** [Files, Shell commands, Configuration instructions] <br>
**Output Format:** [Markdown with inline bash code blocks, CSV, JSONL, WAV audio] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Produces term_seed.csv, pronunciation_overrides.csv, manifest.jsonl, and synthesized WAV audio files in the user's eval directory] <br>

## Skill Version(s): <br>
1.1.0 (source: frontmatter) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
