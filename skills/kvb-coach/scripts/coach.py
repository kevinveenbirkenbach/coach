#!/usr/bin/env python3
"""Keep the operator's coaching profile and switch the coach reminder.

Args:
    --profile: path of the profile JSON file; every command but schedule
        needs it.
    like|dislike <area> <thing>: record a preference; one replaces the other.
    forget <area> <thing>: drop a preference.
    done <area> <thing> [--at <iso>]: log that the operator did it.
    show [--now <iso>] [--json]: likes, dislikes and the last logged activity
        per area with the hours since.
    schedule on|off [--schedules <path>] [--settings <path> ...]: switch the
        coach row of the council's schedules.json through schedules.py set of
        the kvb-org-organize skill, the row the hub's Schedules tab shows; on
        names the install command when no settings file registers the
        reminder hook.

Exit codes:
    0 done, 2 usage error or no schedules.py, else the exit code of
    schedules.py.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

AREAS = ("psyche", "body", "sleep", "food", "tasks", "delegate")
LOG_LIMIT = 500
SCHEDULES = Path(__file__).resolve().parents[2] / "kvb-org-organize" / "scripts" / "schedules.py"
SETTINGS = (Path.home() / ".claude" / "settings.json", Path.home() / ".claude" / "settings.local.json")
HOOK = "kvb-coach/hooks/reminder.sh"
INSTALL = "make -C ~/Repositories/github.com/kevinveenbirkenbach/skills install"


def fail(message: str) -> None:
    print(f"coach: {message}", file=sys.stderr)
    sys.exit(2)


def moment(value: str | None) -> datetime.datetime:
    if value is None:
        return datetime.datetime.now(datetime.UTC)
    try:
        parsed = datetime.datetime.fromisoformat(value)
    except ValueError:
        fail(f"{value} is not an ISO timestamp")
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.UTC)


def load(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"likes": {}, "dislikes": {}, "log": []}
    except ValueError:
        fail(f"{path} is not valid JSON")
    return data


def save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False), encoding="utf-8"
    )
    tmp.replace(path)


def prefer(data: dict, keep: str, area: str, thing: str) -> None:
    for key in ("likes", "dislikes"):
        items = data[key].setdefault(area, [])
        if thing in items:
            items.remove(thing)
    if keep:
        data[keep][area].append(thing)


def summary(data: dict, now: datetime.datetime) -> list[dict]:
    rows = []
    for area in AREAS:
        last = next((e for e in reversed(data["log"]) if e["area"] == area), None)
        hours = None
        if last:
            hours = round((now - moment(last["at"])).total_seconds() / 3600, 1)
        rows.append(
            {
                "area": area,
                "likes": data["likes"].get(area, []),
                "dislikes": data["dislikes"].get(area, []),
                "last": last["thing"] if last else None,
                "hours_ago": hours,
            }
        )
    return rows


def registered(settings: list[Path]) -> bool:
    for path in settings:
        try:
            if HOOK in path.read_text(encoding="utf-8"):
                return True
        except OSError:
            continue
    return False


def schedule(state: str, schedules: Path, settings: list[Path]) -> int:
    """Args:
        state: on or off.
        schedules: the schedules.py of the kvb-org-organize skill.
        settings: the Claude Code settings files that may register the hook.
    """
    if not schedules.is_file():
        print(f"coach: no {schedules}; install the skills repository: {INSTALL}", file=sys.stderr)
        return 2
    done = subprocess.run([sys.executable, "-I", str(schedules), "set", "coach", f"--{state}"], capture_output=True, text=True, check=False)
    if done.returncode:
        print(f"coach: {done.stderr.strip()}", file=sys.stderr)
        return done.returncode
    print(f"coach reminder {state}: {done.stdout.strip()}")
    if state == "on" and not registered(settings):
        print(f"coach: no settings file registers {HOOK} yet; run: {INSTALL}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("schedule")
    p.add_argument("state", choices=("on", "off"))
    p.add_argument("--schedules", type=Path, default=SCHEDULES)
    p.add_argument("--settings", type=Path, action="append")
    for name in ("like", "dislike", "forget"):
        p = sub.add_parser(name)
        p.add_argument("area", choices=AREAS)
        p.add_argument("thing")
    p = sub.add_parser("done")
    p.add_argument("area", choices=AREAS)
    p.add_argument("thing")
    p.add_argument("--at")
    p = sub.add_parser("show")
    p.add_argument("--now")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.cmd == "schedule":
        return schedule(args.state, args.schedules, args.settings or list(SETTINGS))
    if not args.profile:
        fail("--profile is required")

    path = Path(args.profile)
    data = load(path)
    if args.cmd == "show":
        rows = summary(data, moment(args.now))
        if args.json:
            print(json.dumps(rows, indent=1, ensure_ascii=False))
            return 0
        for row in rows:
            last = f"{row['last']} {row['hours_ago']}h ago" if row["last"] else "-"
            print(
                f"{row['area']}\tlast: {last}\tlikes: {', '.join(row['likes']) or '-'}"
                f"\tdislikes: {', '.join(row['dislikes']) or '-'}"
            )
        return 0
    if args.cmd == "done":
        data["log"].append(
            {"area": args.area, "thing": args.thing, "at": moment(args.at).isoformat()}
        )
        data["log"] = data["log"][-LOG_LIMIT:]
    else:
        keep = {"like": "likes", "dislike": "dislikes"}.get(args.cmd, "")
        prefer(data, keep, args.area, args.thing)
    save(path, data)
    print(f"{args.cmd} {args.area} {args.thing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
