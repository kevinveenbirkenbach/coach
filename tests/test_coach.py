"""Exercise coach.py and the reminder: preferences, the log, the schedule switch and the silent reminder while off."""

from __future__ import annotations

import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "kvb-coach" / "scripts" / "coach.py"
HOOK = REPO_ROOT / "skills" / "kvb-coach" / "hooks" / "reminder.sh"
OFF = 3
FAKE_SCHEDULES = """import json, sys
from pathlib import Path
store = Path(__file__).with_name("rows.json")
rows = json.loads(store.read_text()) if store.exists() else {}
if sys.argv[1] == "check":
    row = rows.get(sys.argv[2], {"on": False, "every": 1})
    if not row["on"]:
        sys.exit(3)
    print(row["every"])
elif sys.argv[1] == "set":
    row = rows.get(sys.argv[2], {"on": False, "every": 1})
    row["on"] = sys.argv[3] == "--on"
    rows[sys.argv[2]] = row
    store.write_text(json.dumps(rows, sort_keys=True))
    print(json.dumps(row, sort_keys=True))
"""


class FakeSchedules:
    def __init__(self, folder: Path) -> None:
        self.script = folder / "schedules.py"
        self.rows = folder / "rows.json"
        self.script.write_text(FAKE_SCHEDULES, encoding="utf-8")

    def put(self, rows: dict | None) -> None:
        self.rows.unlink(missing_ok=True)
        if rows is not None:
            self.rows.write_text(json.dumps(rows, sort_keys=True), encoding="utf-8")


class TestCoach(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = Path(self.tmp.name) / "state" / "coach.json"

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--profile", str(self.profile), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def _show(self, now: str) -> dict:
        result = self._run("show", "--now", now, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        return {row["area"]: row for row in json.loads(result.stdout)}

    def test_a_dislike_replaces_a_like_and_forget_drops_it(self):
        self._run("like", "body", "Running")
        self._run("like", "body", "Running")
        self._run("like", "body", "Yoga")
        self._run("dislike", "body", "Running")
        body = self._show("2026-11-03T18:00:00+00:00")["body"]
        self.assertEqual(body["likes"], ["Yoga"])
        self.assertEqual(body["dislikes"], ["Running"])
        self._run("forget", "body", "Running")
        self.assertEqual(self._show("2026-11-03T18:00:00+00:00")["body"]["dislikes"], [])

    def test_the_latest_done_per_area_gives_the_hours_since(self):
        self._run("done", "food", "Breakfast", "--at", "2026-11-03T08:00:00+00:00")
        self._run("done", "food", "Lunch", "--at", "2026-11-03T12:30:00+00:00")
        self._run("done", "sleep", "Night", "--at", "2026-11-02T23:00:00+00:00")
        rows = self._show("2026-11-03T18:00:00+00:00")
        self.assertEqual((rows["food"]["last"], rows["food"]["hours_ago"]), ("Lunch", 5.5))
        self.assertEqual(rows["sleep"]["hours_ago"], 19.0)
        self.assertIsNone(rows["psyche"]["last"])

    def test_invalid_input_exits_2_and_keeps_the_profile(self):
        self.assertEqual(self._run("like", "work", "x").returncode, 2)
        self.assertEqual(self._run("done", "body", "x", "--at", "yesterday").returncode, 2)
        self.assertFalse(self.profile.exists())
        self.profile.parent.mkdir(parents=True)
        self.profile.write_text("{broken", encoding="utf-8")
        self.assertEqual(self._run("show").returncode, 2)
        self.assertEqual(self.profile.read_text(encoding="utf-8"), "{broken")
        done = subprocess.run([sys.executable, str(SCRIPT), "show"], check=False, capture_output=True, text=True)
        self.assertEqual(done.returncode, 2)


class TestSchedule(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.fake = FakeSchedules(self.base)
        self.settings = self.base / "settings.local.json"

    def _schedule(self, state: str, schedules: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "schedule", state, "--schedules", str(schedules or self.fake.script), "--settings", str(self.settings)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_on_and_off_switch_only_the_coach_row_and_keep_the_others(self):
        self.fake.put({"dream": {"on": True, "every": 6}})
        self.settings.write_text(json.dumps({"hooks": {"UserPromptSubmit": [{"hooks": [{"command": "bash ~/.claude/skills/kvb-coach/hooks/reminder.sh"}]}]}}), encoding="utf-8")
        done = self._schedule("on")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertNotIn("run: make", done.stdout)
        self.assertEqual(json.loads(self.fake.rows.read_text(encoding="utf-8")), {"coach": {"on": True, "every": 1}, "dream": {"on": True, "every": 6}})
        self.assertEqual(self._schedule("off").returncode, 0)
        self.assertEqual(json.loads(self.fake.rows.read_text(encoding="utf-8")), {"coach": {"on": False, "every": 1}, "dream": {"on": True, "every": 6}})

    def test_on_without_a_registered_hook_names_the_install_command(self):
        done = self._schedule("on")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("make -C ~/Repositories/github.com/kevinveenbirkenbach/skills install", done.stdout)

    def test_without_the_skills_repository_it_exits_2_and_names_the_install(self):
        done = self._schedule("on", self.base / "missing.py")
        self.assertEqual(done.returncode, 2)
        self.assertIn("install the skills repository", done.stderr)


class TestCoachHour(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.hours = Path(self.tmp.name) / "hours"
        self.fake = FakeSchedules(Path(self.tmp.name))
        self.fake.put({"coach": {"on": True, "every": 1}})

    def _env(self, hour: str, path: str = "/usr/bin:/bin") -> dict:
        return {"PATH": path, "HOME": self.tmp.name, "TZ": "UTC", "COACH_STAMP_DIR": str(self.hours), "COACH_HOUR": hour, "COACH_SCHEDULES": str(self.fake.script)}

    def _run(self, hour: str) -> str:
        return subprocess.run(["bash", str(HOOK)], check=True, capture_output=True, text=True, env=self._env(hour)).stdout

    def test_first_prompt_of_each_hour_triggers_the_coach_once(self):
        self.assertIn("kvb-coach", self._run("2026-11-03T14"))
        self.assertEqual(self._run("2026-11-03T14"), "")
        self.assertIn("kvb-coach", self._run("2026-11-03T15"))
        self.assertEqual(len(list(self.hours.iterdir())), 1)

    def test_every_three_hours_it_speaks_once_per_three_hour_slot(self):
        self.fake.put({"coach": {"on": True, "every": 3}})
        spoken = [hour for hour in range(24) if self._run(f"2026-11-03T{hour:02d}")]
        self.assertEqual(len(spoken), 8)
        self.assertEqual({later - earlier for earlier, later in itertools.pairwise(spoken)}, {3})

    def test_the_row_off_or_no_schedules_script_keeps_it_silent_and_stamps_nothing(self):
        self.fake.put({"coach": {"on": False, "every": 1}})
        self.assertEqual(self._run("2026-11-03T14"), "")
        self.fake.put(None)
        self.assertEqual(self._run("2026-11-03T14"), "")
        self.fake.script.unlink()
        self.assertEqual(self._run("2026-11-03T14"), "")
        self.assertFalse(self.hours.exists())

    def test_the_hour_picks_one_fixed_tip_and_loads_no_skill(self):
        tips = {hour: self._run(f"2026-11-03T{hour}").splitlines() for hour in ("23", "04", "12", "19", "09", "16")}
        firsts = {hour: lines[1].split(" ", 1)[0] for hour, lines in tips.items()}
        self.assertEqual(firsts, {"23": "😴", "04": "😴", "12": "🥗", "19": "🥗", "09": "🚶", "16": "🚶"})
        self.assertTrue(all(len(lines) == 2 and "load no skill" in lines[0] for lines in tips.values()))

    def test_a_binary_planted_on_the_inherited_path_never_runs(self):
        planted = Path(self.tmp.name) / "planted"
        planted.mkdir()
        marker = Path(self.tmp.name) / "ran"
        for name in ("mkdir", "find", "cat", "date", "python3"):
            fake = planted / name
            fake.write_text(f"#!/bin/sh\n/usr/bin/touch '{marker}'\n", encoding="utf-8")
            fake.chmod(0o755)
        subprocess.run(["bash", str(HOOK)], check=True, capture_output=True, text=True, env=self._env("2026-11-03T14", f"{planted}:/usr/bin:/bin"))
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
