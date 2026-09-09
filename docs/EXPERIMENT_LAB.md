# Experiment Lab

Experiments record a hypothesis, baseline prompt, controlled variants, preserved dimensions, target model, evaluation axes, and execution status. V3.2 ships planned experiments but does not claim visual findings because no controlled GPT Image 2 run was executed in this build environment.

## V3.3 host-native execution workflow

V3.3 makes experiment execution host-native first. A run plan assigns opaque
blind IDs to every output slot. `aipf experiment-export <run.json>` creates a
blind-safe generation package containing IDs, prompts, and generation settings
without control/variant labels. Images generated in ChatGPT or another host can
then be recorded with `aipf experiment-import`.

The optional API path remains available for users with API billing, but it is
not required for normal experiment planning, host export, import, or review.
Exact model snapshots must remain `unknown` when the host does not expose them;
the project must not invent snapshot metadata.
