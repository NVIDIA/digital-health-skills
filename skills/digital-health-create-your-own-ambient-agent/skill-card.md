## Description: <br>
Build a custom digital health ambient healthcare voice agent using spec-driven development. <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers building custom ambient healthcare voice agents with NVIDIA Nemotron Voice Agent, LangGraph, and FastAPI through a spec-driven development workflow. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Not Specified] <br>
**Credential Type(s):** [None identified] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [Prerequisite References](references/prerequisite-references.md) <br>
- [Specification Workflow](references/specification-workflow.md) <br>
- [Planning Workflow](references/planning-workflow.md) <br>
- [Implementation Guide](references/implementation-guide.md) <br>
- [Validation and Handoff](references/validation-handoff.md) <br>
- [Design Requirements Guide](references/design-requirements-guide.md) <br>
- [Output Repo Template](references/output-repo-template.md) <br>
- [Nemotron Voice Agent Deploy Skill](references/nemotron-voice-agent-deploy-skill.md) <br>
- [Workflow Flowchart](references/workflow-flowchart.md) <br>
- [AgentSkills.io Specification](https://agentskills.io/specification) <br>


## Skill Output: <br>
**Output Type(s):** [Code, Files, Configuration instructions] <br>
**Output Format:** [Repository scaffold with Python, YAML, Dockerfile, and Markdown files] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [None] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
Evaluated against 10 evaluation tasks in the astra-sandbox environment using the NVSkills-Eval external profile with 1 attempt per task. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Verifies that the agent loaded the expected skill and workflow. <br>
- `skill_efficiency`: Checks routing quality, decoy avoidance, and redundant tool usage. <br>
- `accuracy`: Grades final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Checks whether the overall user task completed successfully. <br>
- `behavior_check`: Verifies expected behavior steps, including safety expectations. <br>
- `token_efficiency`: Compares token usage with and without the skill. <br>



## Evaluation Results: <br>
| Dimension | Num | `claude-code` | `codex` |
|---|---:|---:|---:|
| Security | 5 | 100% (+0%) | 100% (+10%) |
| Correctness | 5 | 94% (+32%) | 98% (+32%) |
| Discoverability | 5 | 100% (+42%) | 94% (+32%) |
| Effectiveness | 5 | 90% (+30%) | 96% (+32%) |
| Efficiency | 5 | 94% (+35%) | 87% (+25%) |

## Skill Version(s): <br>
1.0.0 (source: frontmatter) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
