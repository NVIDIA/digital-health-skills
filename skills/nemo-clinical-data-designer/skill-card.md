## Description: <br>
Use when generating synthetic tabular datasets via Data Designer — sampler columns, LLM columns, custom generators. Not for ASR audio. <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and data scientists generating synthetic tabular datasets for clinical and healthcare applications using NeMo Data Designer. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Output Template](references/output-template.md) <br>
- [Person Sampling](references/person-sampling.md) <br>
- [Preview & Review](references/preview-review.md) <br>
- [Seed Datasets](references/seed-datasets.md) <br>
- [Interactive Workflow](workflows/interactive.md) <br>
- [Autopilot Workflow](workflows/autopilot.md) <br>


## Skill Output: <br>
**Output Type(s):** [Code, Files] <br>
**Output Format:** [Python script with PEP 723 inline metadata header] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Exports load_config_builder() returning a DataDesignerConfigBuilder] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
1 evaluation task with 2 attempts per task; pass threshold 50%. Evaluated under NVSkills-Eval external profile in local environment. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>

Underlying evaluation signals used in this run: <br>
- `skill_execution`: Verifies that the agent loaded the expected skill and workflow. <br>
- `skill_efficiency`: Checks routing quality, decoy avoidance, and redundant tool usage. <br>
- `accuracy`: Grades final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Checks whether the overall user task completed successfully. <br>
- `behavior_check`: Verifies expected behavior steps, including safety expectations. <br>
- `token_efficiency`: Compares token usage with and without the skill. <br>



## Evaluation Results: <br>
| Dimension | Num | `claude-code` | `codex` |
|---|---:|---:|---:|
| Security | 2 | 75% (+38%) | 62% (+25%) |
| Correctness | 2 | 72% (-24%) | 74% (-14%) |
| Discoverability | 2 | 85% (-5%) | 81% (+14%) |
| Effectiveness | 2 | 61% (+2%) | 47% (-22%) |
| Efficiency | 2 | 85% (+15%) | 75% (+19%) |

## Skill Version(s): <br>
466af14 (source: git SHA, committed 2026-05-28) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
