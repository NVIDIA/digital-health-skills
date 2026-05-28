## Description: <br>
Use when the user wants to deploy, run, or test an ASR (speech-to-text) Riva NIM — cloud-hosted (build.nvidia.com) or self-hosted Parakeet/Canary/Whisper. <br>

This skill is ready for commercial/non-commercial use. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers deploying, running, or testing NVIDIA Riva ASR (speech-to-text) NIM services for cloud-hosted or self-hosted transcription workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [ASR Support Matrix](https://docs.nvidia.com/nim/speech/latest/reference/support-matrix/asr.html) <br>
- [ASR Performance Benchmarks](https://docs.nvidia.com/nim/speech/latest/reference/performances/asr/performance.html) <br>
- [Riva Python Clients](https://github.com/nvidia-riva/python-clients) <br>


## Skill Output: <br>
**Output Type(s):** [Shell commands, Configuration instructions, API Calls] <br>
**Output Format:** [Markdown with inline bash code blocks] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [None] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
Evaluated against 1 evaluation task (1 positive skill-activation case, 2 attempts per task, 50% pass threshold). <br>

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
| Security | 2 | 83% (+0%) | 100% (+33%) |
| Correctness | 2 | 100% (+5%) | 92% (-3%) |
| Discoverability | 2 | 100% (+9%) | 80% (-4%) |
| Effectiveness | 2 | 81% (+9%) | 80% (+20%) |
| Efficiency | 2 | 93% (+23%) | 78% (+8%) |

## Skill Version(s): <br>
1.0.0 (source: frontmatter) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
