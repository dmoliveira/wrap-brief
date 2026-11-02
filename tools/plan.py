"""Validate and render the public delivery plan without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
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


def public_file(root: Path, value: str, *, evidence: bool = False) -> Path:
    require(isinstance(value, str) and bool(value), "file reference must be text")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe path: {value}")
    require((root / path).resolve().is_relative_to(root.resolve()), f"escaped path: {value}")
    require((root / path).is_file(), f"missing file: {value}")
    if evidence:
        require(value not in GENERATED, "generated progress is not completion evidence")
        require(not any(p.startswith(".") for p in path.parts), "private evidence path")
        require(path.suffix not in SENSITIVE_SUFFIXES, "sensitive evidence file")
        require(not (root / path).is_symlink(), "symlink evidence is not allowed")
        require(
            root / path in project_files(root), "evidence is not a public publication candidate"
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


def evidence_list(root: Path, values: list, label: str) -> None:
    require(isinstance(values, list) and values, f"{label}: evidence required")
    for value in values:
        public_file(root, value, evidence=True)


def milestone_done(data: dict, id: str) -> bool:
    tasks = {t["id"]: t for t in data["tasks"]}
    milestone = next((m for m in data["milestones"] if m["id"] == id), None)
    return bool(milestone and milestone["tasks"]) and all(
        tasks[t]["status"] == "done" for t in milestone["tasks"]
    )


def validate(data: dict, root: Path) -> None:
    require(isinstance(data, dict) and data.get("schema_version") == 1, "unsupported schema")
    project = data.get("project", {})
    require(isinstance(project, dict) and project.get("name"), "project name required")
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", project.get("updated", "")), "invalid plan date")
    require(project.get("max_parallel_lanes") in (1, 2), "parallel lane limit must be 1 or 2")
    scopes = unique_index(data.get("scopes"), r"planning|mvp|growth|revenue|future", "scope")
    require(set(scopes) == SCOPES, "all scope definitions required")
    enabled = project.get("enabled_scopes")
    require(
        isinstance(enabled, list) and len(enabled) == len(set(enabled)), "invalid enabled scopes"
    )
    require(
        set(enabled) <= SCOPES and {"planning", "mvp"} <= set(enabled), "invalid scope activation"
    )
    for scope in scopes.values():
        require(scope.get("activation"), "scope activation rule required")
    epics = unique_index(data.get("epics"), r"E\d{2}", "epic")
    tasks = unique_index(data.get("tasks"), r"T\d{2}\.\d{2}", "task")
    milestones = unique_index(data.get("milestones"), r"M\d+", "milestone")
    require(epics and tasks and milestones, "epics, tasks and milestones required")
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
        require(isinstance(ids, list) and len(ids) == len(set(ids)), "invalid milestone tasks")
        require(all(t in tasks for t in ids), "missing milestone task")
        require(ids or milestone["id"] == "M5", "only portfolio milestone M5 may be empty")
    subtask_ids = set()
    for id, task in tasks.items():
        require(
            task.get("epic") in epics and task["epic"] == "E" + id[1:3], f"{id}: invalid parent"
        )
        require(task.get("scope") in SCOPES, f"{id}: invalid scope")
        require(task.get("milestone") in milestones, f"{id}: invalid milestone")
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
        require(
            isinstance(deps, list) and len(deps) == len(set(deps)), f"{id}: invalid dependencies"
        )
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
        for subtask in task["subtasks"]:
            require(isinstance(subtask, dict), f"{id}: invalid subtask")
            sid = subtask.get("id", "")
            require(
                isinstance(sid, str) and re.fullmatch(re.escape(id) + r"\.\d+", sid),
                f"{id}: invalid subtask ID",
            )
            require(sid not in subtask_ids, f"duplicate subtask: {sid}")
            subtask_ids.add(sid)
            require(
                subtask.get("title") and subtask.get("done_when"), f"{sid}: done criterion required"
            )
            require(subtask.get("status") in STATES, f"{sid}: invalid status")
            if subtask["status"] == "done":
                require(
                    task["status"] not in {"not_started", "canceled"},
                    f"{sid}: inconsistent parent status",
                )
                evidence_list(root, subtask.get("evidence"), sid)
        completion = task.get("completion")
        require(isinstance(completion, dict), f"{id}: completion record required")
        if task["status"] == "done":
            require(
                all(s["status"] == "done" for s in task["subtasks"]), f"{id}: unfinished subtask"
            )
            evidence_list(root, completion.get("evidence"), id)
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
                public_file(root, check.get("evidence"), evidence=True)
            review = completion.get("review")
            require(
                isinstance(review, dict) and review.get("result") == "pass",
                f"{id}: passing review required",
            )
            public_file(root, review.get("evidence"), evidence=True)
    visiting, visited = set(), set()

    def visit(id: str) -> None:
        require(id not in visiting, f"dependency cycle at {id}")
        if id in visited:
            return
        visiting.add(id)
        for dep in tasks[id]["depends_on"]:
            visit(dep)
        visiting.remove(id)
        visited.add(id)

    for id in tasks:
        visit(id)
    for scope, gate in (("growth", "M2"), ("revenue", "M3"), ("future", "M2")):
        if scope in enabled:
            require(milestone_done(data, gate), f"{scope}: incomplete activation gate {gate}")
            evidence_list(root, project.get("activation_evidence", {}).get(scope), scope)


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
    lines += ["", "## Milestones", "", "| Gate | Outcome | Status |", "| --- | --- | --- |"]
    for m in data["milestones"]:
        status = (
            "portfolio, select only justified tasks"
            if not m["tasks"]
            else "done"
            if milestone_done(data, m["id"])
            else "not complete"
        )
        lines.append(f"| {m['id']} | {m['title']} | {status} |")
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
                f"**Status:** {t['status']} · **Scope:** {t['scope']} · **Milestone:** {t['milestone']} · **Risk:** {t['risk']} · **Size:** {t['size']}",
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
                f"- All named checks pass: {', '.join(t['verification'])}; independent review and public-safe evidence recorded.",
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
            path.suffix not in {".sqlite", ".sqlite3", ".db", ".pem", ".key", ".p12", ".pfx"},
            f"sensitive file: {relative}",
        )
        require(
            not path.name.startswith(".env") or path.name == ".env.example",
            f"environment file: {relative}",
        )
        text = path.read_text(encoding="utf-8")
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
