# Evaluation Report

Evaluation of the `riva-tts` skill before publication through NVSkills-Eval.

This benchmark summarizes 3-Tier Evaluation from NVSkills-Eval results for the skill. The goal is to document whether the skill is safe, discoverable, effective, and useful for agents before it is published for broader workflow use.

## Evaluation Summary

- Skill: `riva-tts`
- Evaluation date: 2026-05-28
- NVSkills-Eval profile: `external`
- Environment: `local`
- Dataset: 1 evaluation tasks
- Attempts per task: 2
- Pass threshold: 50%
- Overall verdict: FAIL

## Agents Used

- `claude-code`
- `codex`

## Metrics Used

Reported benchmark dimensions:

- Security: checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access.
- Correctness: checks whether the agent follows the expected workflow and produces the correct final output.
- Discoverability: checks whether the agent loads the skill when relevant and avoids using it when irrelevant.
- Effectiveness: checks whether the agent performs measurably better with the skill than without it.
- Efficiency: checks whether the agent uses fewer tokens and avoids redundant work.

Underlying evaluation signals used in this run:

- `skill_execution` (Skill Execution): verifies that the agent loaded the expected skill and workflow.
- `skill_efficiency` (Efficiency): checks routing quality, decoy avoidance, and redundant tool usage.
- `accuracy` (Accuracy): grades final-answer correctness against the reference answer.
- `goal_accuracy` (Goal Accuracy): checks whether the overall user task completed successfully.
- `behavior_check` (Behavior Check): verifies expected behavior steps, including safety expectations.
- `token_efficiency` (Token Efficiency): compares token usage with and without the skill.

## Test Tasks

The benchmark dataset contained 1 evaluation tasks:

- Positive tasks: 1 tasks where the skill was expected to activate.
- Negative tasks: 0 tasks where no skill was expected.
- Unlabeled tasks: 0 tasks where positive/negative intent could not be inferred.

Task composition is derived from the evaluation dataset when possible. Entries with `expected_skill` set are treated as positive skill-activation cases, while entries with `expected_skill: null` are treated as negative activation cases.

## Results

| Dimension | Num | `claude-code` | `codex` |
|---|---:|---:|---:|
| Security | 2 | 100% (+0%) | 100% (+50%) |
| Correctness | 2 | 100% (+0%) | 92% (+2%) |
| Discoverability | 2 | 94% (+4%) | 80% (+4%) |
| Effectiveness | 2 | 89% (+1%) | 88% (+23%) |
| Efficiency | 2 | 83% (+11%) | 78% (+10%) |

Score values show skill-assisted performance. Values in parentheses show uplift versus the no-skill baseline when baseline data is available.

## Tier 1: Static Validation Summary

Tier 1 validation passed with observations. NVSkills-Eval ran 9 checks and found 3 total findings.

Top findings:

- MEDIUM SECURITY/Unknown (SQP-2): The skill-card description and output type section acknowledge that shell commands are generated (Output Type: Shell com (`skill-card.md:27`)
- LOW SCHEMA/unexpected_file: Unexpected 'skill.oms.sig' in skill root (`skills/riva-tts/skill.oms.sig`)
- LOW SCHEMA/unexpected_file: Unexpected 'skill-card.md' in skill root (`skills/riva-tts/skill-card.md`)

## Tier 2: Deduplication Summary

Tier 2 validation reported findings. NVSkills-Eval ran 2 checks and found 1 total findings.

Top findings:

- HIGH DUPLICATE/duplicate: Duplicate content found within SKILL.md:
  "# Riva TTS NIM" in SKILL.md (lines 1-10)
  vs "## Prerequisites" in SKILL.md (lines 21-26)
  vs "## Option B — Self-Hosted NIM Deployment" in SKILL.md (lines 71-76) (`SKILL.md:1`)

## Publication Recommendation

The skill should be reviewed before NVSkills-Eval publication. Skill owners should address the findings above and rerun NVSkills-Eval to refresh this benchmark.
