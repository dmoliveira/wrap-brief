"""Validate and render the public delivery plan without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = Path("docs/plan/backlog.json")
STATES = {"not_started", "in_progress", "blocked", "review", "done", "canceled"}
SCOPES = {"planning", "mvp", "growth", "revenue", "future"}
GENERATED = {"docs/plan/STATUS.md", "docs/plan/BACKLOG.md"}
SENSITIVE_SUFFIXES = {".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx"}


def require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def public_file(
    root: Path, value: str, *, evidence: bool = False, candidates: set[Path] | None = None
) -> Path:
    require(isinstance(value, str) and bool(value), "file reference must be text")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe path: {value}")
    require((root / path).resolve().is_relative_to(root.resolve()), f"escaped path: {value}")
    require((root / path).is_file(), f"missing file: {value}")
    if evidence:
        require(path.as_posix() not in GENERATED, "generated progress is not completion evidence")
        require(not any(p.startswith(".") for p in path.parts), "private evidence path")
        require(path.suffix.lower() not in SENSITIVE_SUFFIXES, "sensitive evidence file")
        require(not (root / path).is_symlink(), "symlink evidence is not allowed")
        require(
            root / path in (candidates if candidates is not None else set(project_files(root))),
            "evidence is not a public publication candidate",
        )
    return root / path


def unique_index(records: list, pattern: str, label: str) -> dict:
    require(isinstance(records, list), f"{label} must be a list")
    result = {}
    for record in records:
        require(isinstance(record, dict), f"invalid {label} record")
        key = record.get("id", "")
        require(isinstance(key, str) and re.fullmatch(pattern, key), f"invalid {label} ID: {key}")
        require(key not in result, f"duplicate {label} ID: {key}")
        result[key] = record
    return result


def text(value: object, label: str) -> None:
    require(isinstance(value, str) and value.strip(), f"{label}: nonempty text required")


def text_list(value: object, label: str, *, allow_empty: bool = False) -> None:
    require(isinstance(value, list) and (allow_empty or value), f"{label}: list required")
    require(all(isinstance(v, str) and v.strip() for v in value), f"{label}: invalid text entry")
    require(len(value) == len(set(value)), f"{label}: duplicate entry")


def evidence_list(
    root: Path, values: list, label: str, candidates: set[Path] | None = None
) -> None:
    require(isinstance(values, list) and values, f"{label}: evidence required")
    for value in values:
        public_file(root, value, evidence=True, candidates=candidates)


def check_dag(records: dict, label: str) -> None:
    visiting, visited = set(), set()

    def visit(id: str) -> None:
        require(id not in visiting, f"{label} dependency cycle at {id}")
        if id in visited:
            return
        visiting.add(id)
        for dep in records[id]["depends_on"]:
            visit(dep)
        visiting.remove(id)
        visited.add(id)

    for id in records:
        visit(id)


def milestone_done(data: dict, id: str) -> bool:
    tasks = {t["id"]: t for t in data["tasks"]}
    milestone = next((m for m in data["milestones"] if m["id"] == id), None)
    return bool(milestone and milestone["kind"] == "gate" and milestone["tasks"]) and (
        all(tasks[t]["status"] == "done" for t in milestone["tasks"])
        and all(milestone_done(data, dep) for dep in milestone["depends_on"])
    )


def validate(data: dict, root: Path) -> None:
    require(
        isinstance(data, dict)
        and type(data.get("schema_version")) is int
        and data["schema_version"] == 1,
        "unsupported schema",
    )
    project = data.get("project", {})
    require(isinstance(project, dict), "project must be an object")
    text(project.get("name"), "project name")
    updated = project.get("updated")
    require(
        isinstance(updated, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", updated),
        "invalid plan date",
    )
    try:
        date.fromisoformat(updated)
    except ValueError as error:
        raise ValueError("invalid plan date") from error
    lanes = project.get("max_parallel_lanes")
    require(type(lanes) is int and lanes in (1, 2), "parallel lane limit must be 1 or 2")
    scopes = unique_index(data.get("scopes"), r"planning|mvp|growth|revenue|future", "scope")
    require(set(scopes) == SCOPES, "all scope definitions required")
    enabled = project.get("enabled_scopes")
    text_list(enabled, "enabled scopes")
    require(
        set(enabled) <= SCOPES and {"planning", "mvp"} <= set(enabled), "invalid scope activation"
    )
    for scope in scopes.values():
        require(scope.get("activation"), "scope activation rule required")
    epics = unique_index(data.get("epics"), r"E\d{2}", "epic")
    tasks = unique_index(data.get("tasks"), r"T\d{2}\.\d{2}", "task")
    milestones = unique_index(data.get("milestones"), r"M\d+", "milestone")
    require(epics and tasks and milestones, "epics, tasks and milestones required")
    candidates = set(project_files(root))
    for epic in epics.values():
        require(
            all(epic.get(k) for k in ("title", "owner", "objective", "spec")),
            "epic fields required",
        )
        public_file(root, epic["spec"])
        require(any(t.get("epic") == epic["id"] for t in tasks.values()), "empty epic")
    for milestone in milestones.values():
        require(
            all(milestone.get(k) for k in ("title", "owner", "entry", "exit")),
            "milestone fields required",
        )
        ids = milestone.get("tasks")
        text_list(ids, "milestone tasks", allow_empty=True)
        require(all(t in tasks for t in ids), "missing milestone task")
        require(milestone.get("kind") in {"gate", "portfolio"}, "invalid milestone kind")
        require(
            ids if milestone["kind"] == "gate" else not ids,
            "invalid milestone gate/portfolio members",
        )
        deps = milestone.get("depends_on")
        text_list(deps, "milestone dependencies", allow_empty=True)
        require(
            all(d in milestones and d != milestone["id"] for d in deps),
            "invalid milestone dependency",
        )
    check_dag(milestones, "milestone")
    subtask_ids = set()
    for id, task in tasks.items():
        require(
            task.get("epic") in epics and task["epic"] == "E" + id[1:3], f"{id}: invalid parent"
        )
        require(
            isinstance(task.get("scope"), str) and task["scope"] in SCOPES, f"{id}: invalid scope"
        )
        require(task.get("milestone") in milestones, f"{id}: invalid milestone")
        require(type(task.get("gate_required")) is bool, f"{id}: gate_required must be boolean")
        require(task.get("status") in STATES, f"{id}: invalid status")
        require(task.get("risk") in {"low", "medium", "high"}, f"{id}: invalid risk")
        require(task.get("size") in {"XS", "S", "M"}, f"{id}: split oversized task")
        for key in ("title", "owner", "deliverable"):
            require(isinstance(task.get(key), str) and task[key].strip(), f"{id}: missing {key}")
        for key in ("paths", "acceptance", "verification", "subtasks"):
            require(isinstance(task.get(key), list) and task[key], f"{id}: missing {key}")
        for key in ("paths", "acceptance", "verification"):
            require(
                all(isinstance(v, str) and v.strip() for v in task[key]), f"{id}: invalid {key}"
            )
        require(
            len(set(task["verification"])) == len(task["verification"]),
            f"{id}: duplicate verification",
        )
        for path in task["paths"]:
            require(
                not Path(path).is_absolute() and ".." not in Path(path).parts,
                f"{id}: unsafe reservation",
            )
        deps = task.get("depends_on")
        text_list(deps, f"{id}: dependencies", allow_empty=True)
        require(all(d in tasks and d != id for d in deps), f"{id}: missing/self dependency")
        if task["scope"] in {"planning", "mvp"}:
            require(
                all(tasks[d].get("scope") in {"planning", "mvp"} for d in deps),
                f"{id}: later scope blocks MVP",
            )
        if task["status"] in {"in_progress", "review", "done"}:
            require(
                all(tasks[d].get("status") == "done" for d in deps), f"{id}: unfinished dependency"
            )
            require(task["scope"] in enabled, f"{id}: active work in disabled scope")
        require(isinstance(task.get("block_reason"), str), f"{id}: reason field required")
        if task["status"] in {"blocked", "canceled"}:
            require(task["block_reason"].strip(), f"{id}: block/cancel reason required")
        else:
            require(not task["block_reason"], f"{id}: stale block/cancel reason")
        for subtask in task["subtasks"]:
            require(isinstance(subtask, dict), f"{id}: invalid subtask")
            sid = subtask.get("id", "")
            require(
                isinstance(sid, str) and re.fullmatch(re.escape(id) + r"\.\d+", sid),
                f"{id}: invalid subtask ID",
            )
            require(sid not in subtask_ids, f"duplicate subtask: {sid}")
            subtask_ids.add(sid)
            text(subtask.get("title"), f"{sid}: title")
            text(subtask.get("done_when"), f"{sid}: done criterion")
            require(subtask.get("status") in STATES, f"{sid}: invalid status")
            text_list(subtask.get("evidence"), f"{sid}: evidence", allow_empty=True)
            if task["status"] == "not_started":
                require(subtask["status"] == "not_started", f"{sid}: inconsistent parent status")
            if subtask["status"] in {"in_progress", "review", "blocked"}:
                require(
                    task["status"] in {"in_progress", "review", "blocked"},
                    f"{sid}: inconsistent parent status",
                )
            if subtask["status"] == "done":
                require(
                    task["status"] != "not_started",
                    f"{sid}: inconsistent parent status",
                )
                evidence_list(root, subtask.get("evidence"), sid, candidates)
            else:
                require(
                    not subtask["evidence"], f"{sid}: unfinished subtask has completion evidence"
                )
        completion = task.get("completion")
        require(isinstance(completion, dict), f"{id}: completion record required")
        text_list(completion.get("evidence"), f"{id}: completion evidence", allow_empty=True)
        require(isinstance(completion.get("checks"), list), f"{id}: checks required")
        if task["status"] != "done":
            require(
                completion == {"evidence": [], "checks": [], "review": None},
                f"{id}: stale completion claims",
            )
        if task["status"] == "done":
            require(
                all(s["status"] == "done" for s in task["subtasks"]), f"{id}: unfinished subtask"
            )
            evidence_list(root, completion.get("evidence"), id, candidates)
            checks = completion.get("checks")
            require(isinstance(checks, list), f"{id}: checks required")
            require(all(isinstance(c, dict) for c in checks), f"{id}: invalid check record")
            require(len(checks) == len(task["verification"]), f"{id}: check coverage mismatch")
            require(
                {c.get("name") for c in checks} == set(task["verification"]),
                f"{id}: missing named check",
            )
            for check in checks:
                require(check.get("result") == "pass", f"{id}: failed verification")
                public_file(root, check.get("evidence"), evidence=True, candidates=candidates)
            review = completion.get("review")
            require(
                isinstance(review, dict) and review.get("result") == "pass",
                f"{id}: passing review required",
            )
            public_file(root, review.get("evidence"), evidence=True, candidates=candidates)
    for milestone in milestones.values():
        expected = {
            t["id"]
            for t in tasks.values()
            if t["milestone"] == milestone["id"] and t["gate_required"]
        }
        require(
            set(milestone["tasks"]) == expected,
            f"{milestone['id']}: milestone/task membership mismatch",
        )
    check_dag(tasks, "task")
    for scope, gate in (("growth", "M2"), ("revenue", "M3"), ("future", "M2")):
        if scope in enabled:
            require(milestone_done(data, gate), f"{scope}: incomplete activation gate {gate}")
            activations = project.get("activation_evidence", {})
            require(isinstance(activations, dict), "activation evidence must be an object")
            evidence_list(root, activations.get(scope), scope, candidates)


def ready(data: dict) -> list[dict]:
    tasks = {t["id"]: t for t in data["tasks"]}
    return [
        t
        for t in data["tasks"]
        if t["scope"] in data["project"]["enabled_scopes"]
        and t["status"] == "not_started"
        and all(tasks[d]["status"] == "done" for d in t["depends_on"])
    ]


def count(tasks: list[dict]) -> str:
    canceled = sum(t["status"] == "canceled" for t in tasks)
    total = len(tasks) - canceled
    done = sum(t["status"] == "done" for t in tasks)
    return (
        f"{done}/{total} ({100 * done / total:.0f}%) · {canceled} canceled"
        if total
        else f"No committed tasks · {canceled} canceled"
    )


def render_status(data: dict) -> str:
    lines = [
        "# Wrap Brief — progress",
        "",
        "> Generated from backlog.json; do not edit. Task-count progress is not effort-weighted.",
        "",
        f"Plan updated: {data['project']['updated']}. **Product is not implemented merely because planning is complete.**",
        "",
        "## Scope progress",
        "",
        "| Scope | Enabled | Completed tasks |",
        "| --- | --- | --- |",
    ]
    for scope in data["scopes"]:
        lines.append(
            f"| {scope['id']} | {'yes' if scope['id'] in data['project']['enabled_scopes'] else 'no'} | {count([t for t in data['tasks'] if t['scope'] == scope['id']])} |"
        )
    lines += [
        "",
        "## Milestones",
        "",
        "| Gate | Outcome | Prerequisite gates | Status |",
        "| --- | --- | --- | --- |",
    ]
    for m in data["milestones"]:
        status = (
            "portfolio, select only justified tasks"
            if m["kind"] == "portfolio"
            else "done"
            if milestone_done(data, m["id"])
            else "not complete"
        )
        lines.append(
            f"| {m['id']} | {m['title']} | {', '.join(m['depends_on']) or 'none'} | {status} |"
        )
    lines += [
        "",
        "## Epics",
        "",
        "| ID | Component | Task progress | Subtasks done |",
        "| --- | --- | --- | --- |",
    ]
    for epic in data["epics"]:
        tasks = [t for t in data["tasks"] if t["epic"] == epic["id"]]
        subs = [s for t in tasks if t["status"] != "canceled" for s in t["subtasks"]]
        lines.append(
            f"| {epic['id']} | {epic['title']} | {count(tasks)} | {sum(s['status'] == 'done' for s in subs)}/{len(subs)} |"
        )
    lines += ["", "## Active and blocked", ""]
    active = [t for t in data["tasks"] if t["status"] in {"in_progress", "review", "blocked"}]
    lines += [
        f"- **{t['id']}** — {t['title']} · {t['status']}"
        + (f" · {t['block_reason']}" if t["block_reason"] else "")
        for t in active
    ] or ["- None."]
    lines += [
        "",
        "## Dependency-ready work",
        "",
        "Choose at most two disjoint lanes; readiness is not permission to overlap shared files.",
        "",
    ]
    lines += [f"- **{t['id']}** — {t['title']} ({t['owner']})" for t in ready(data)] or [
        "- None; finish active work or resolve dependencies first."
    ]
    lines += ["", "## Disabled-scope rules", ""]
    lines += [
        f"- **{s['id']}**: {s['activation']}"
        for s in data["scopes"]
        if s["id"] not in data["project"]["enabled_scopes"]
    ]
    lines += [
        "",
        "[Full backlog](BACKLOG.md) · [Roadmap](new/roadmap.md) · [Schema](schema.md)",
        "",
    ]
    return "\n".join(lines)


def render_backlog(data: dict) -> str:
    lines = [
        "# Wrap Brief — epics, tasks, and subtasks",
        "",
        "> Generated from backlog.json; do not edit. Product work is unimplemented unless explicitly done with evidence.",
        "",
        "Every task also inherits the global definition of done in [delivery workflow](../delivery-workflow.md). Later scopes are refinement plans, not a commitment to build every feature.",
        "",
    ]
    for epic in data["epics"]:
        spec = "../" + epic["spec"].removeprefix("docs/")
        lines += [
            f"## {epic['id']} — {epic['title']}",
            "",
            f"**Owner:** {epic['owner']}. **Outcome:** {epic['objective']} [Specification]({spec}).",
            "",
        ]
        for t in [t for t in data["tasks"] if t["epic"] == epic["id"]]:
            lines += [
                f"### {t['id']} — {t['title']}",
                "",
                f"**Status:** {t['status']} · **Scope:** {t['scope']} · **Milestone:** {t['milestone']} ({'required' if t['gate_required'] else 'optional'}) · **Risk:** {t['risk']} · **Size:** {t['size']}",
                f"**Owner:** {t['owner']}",
                f"**Dependencies:** {', '.join(t['depends_on']) or 'none'}",
                f"**Reserved paths:** {', '.join('`' + p + '`' for p in t['paths'])}",
                "",
                f"**Deliverable:** {t['deliverable']}",
                "",
                "**Done criteria:**",
            ]
            lines += [f"- {criterion}" for criterion in t["acceptance"]]
            lines += [
                f"**Required checks:** {', '.join(t['verification'])}.",
                "",
                "**Subtasks:**",
            ]
            for s in t["subtasks"]:
                lines += [
                    f"- [{'x' if s['status'] == 'done' else ' '}] **{s['id']}** {s['title']} — `{s['status']}`. Done when: {s['done_when']}"
                ]
            if t["block_reason"]:
                lines += ["", f"**Block/cancel reason:** {t['block_reason']}"]
            if t["completion"]["evidence"]:
                lines += [
                    "",
                    "**Completion evidence:** "
                    + ", ".join(f"[{p}](../../{p})" for p in t["completion"]["evidence"]),
                ]
            lines += [""]
    return "\n".join(lines)


def project_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [root / p.decode() for p in result.stdout.split(b"\0") if p]


def check_publication(root: Path) -> None:
    forbidden = {".opencode", ".codememory", ".local", ".env", ".venv", "node_modules"}
    patterns = [
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"gh[pousr]_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"/(?:Users|home)/[A-Za-z0-9_.-]+/",
        r"ses_[A-Za-z0-9]{12,}",
    ]
    for path in project_files(root):
        relative = path.relative_to(root)
        require(
            not any(p in forbidden for p in relative.parts), f"private tracked path: {relative}"
        )
        require(not path.is_symlink(), f"unreviewed symlink: {relative}")
        require(
            path.suffix.lower() not in SENSITIVE_SUFFIXES,
            f"sensitive file: {relative}",
        )
        require(
            not path.name.startswith(".env") or path.name == ".env.example",
            f"environment file: {relative}",
        )
        # ASCII token/path patterns remain detectable even inside non-UTF-8 assets.
        text = path.read_bytes().decode("utf-8", errors="replace")
        for pattern in patterns:
            require(not re.search(pattern, text), f"possible private material in {relative}")
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]]*\]\(([^)\s]+)\)", text):
                if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                destination = (path.parent / target.split("#", 1)[0]).resolve()
                require(
                    destination.is_relative_to(root.resolve()),
                    f"link escapes repository: {relative}",
                )
                require(destination.exists(), f"broken link in {relative}: {target}")


def generated(data: dict) -> dict[str, str]:
    return {
        "docs/plan/STATUS.md": render_status(data),
        "docs/plan/BACKLOG.md": render_backlog(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "render", "next"))
    args = parser.parse_args()
    try:
        data = json.loads((ROOT / BACKLOG).read_text())
        validate(data, ROOT)
        if args.command == "next":
            for task in ready(data):
                print(f"{task['id']} [{task['scope']}] {task['title']}")
            return 0
        for path, text in generated(data).items():
            if args.command == "render":
                (ROOT / path).write_text(text)
            else:
                require(
                    (ROOT / path).read_text() == text,
                    f"generated drift: {path}; run make render-plan",
                )
        if args.command == "check":
            check_publication(ROOT)
        print(f"Plan {args.command}: OK ({len(data['epics'])} epics, {len(data['tasks'])} tasks)")
        return 0
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Plan {args.command}: FAIL: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
