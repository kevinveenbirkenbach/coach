---
name: kvb-coach-on
description: >
  Switch the coach's reminder on: a one-line health tip at the first prompt
  every N hours, once across all agents.
---

Run `${CLAUDE_SKILL_DIR}/../kvb-coach/scripts/coach.py schedule on` and show
its output. It sets the `coach` row of the council's `schedules.json`, the
row the hub's Controls › Schedules tab shows; retime it there or with
`kvb-org-organize/scripts/schedules.py set coach --every <hours>`.

When the output names the install command, the reminder hook is not
registered yet: hand the operator that command through the
`kvb-org-operator` skill; never edit a settings file yourself. An exit code
2 means the skills repository is not installed: hand over the same command.
