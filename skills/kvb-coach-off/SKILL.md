---
name: kvb-coach-off
description: >
  Switch the coach's reminder off; the coach itself stays available on
  request.
---

Run `${CLAUDE_SKILL_DIR}/../kvb-coach/scripts/coach.py schedule off` and show
its output. It clears the `coach` row of the council's `schedules.json`, the
row the hub's Controls › Schedules tab shows; the reminder hook stays
registered and prints nothing while the row is off. An exit code 2 means the
skills repository is not installed: hand the operator the command it names
through the `kvb-org-operator` skill.
