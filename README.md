# Coach 🧘

Agent skills that look after the operator while agents work: a coach for the
next step (psyche, body, sleep, food, own and delegable tasks), a short
guided meditation, and a reminder that is off until you switch it on.

| Skill | What it does |
| --- | --- |
| `kvb-coach` | Coaches the next step on request; keeps a host-local profile of likes, dislikes and what was done. |
| `kvb-coach-on` | Switches the reminder on: one health tip at the first prompt every N hours, once across all agents. |
| `kvb-coach-off` | Switches the reminder off; the coach stays available on request. |
| `kvb-coach-meditation` | A short meditation in the browser with generative alpha-wave music, a breathing fractal and cues, tuned by feedback. |

## Install

The [skills](https://github.com/kevinveenbirkenbach/skills) repository pins
these skills in its `skills-lock.json` and installs them with `make install`,
which also registers the reminder hook. The reminder starts off: switch it
with `/kvb-coach-on` and `/kvb-coach-off`, or in the Agent Orchestrator under
Controls › Schedules, where you also set its interval.

The switch and the reminder use `kvb-org-organize/scripts/schedules.py` of
the skills repository; without it the reminder stays silent.

## Development

```bash
make test
```

The skills came from skills commit
`e5fd70e1831192a79187dc6b54bd187444695959` (requirement 058 of that
repository).

## License

MIT, see [LICENSE](LICENSE).
