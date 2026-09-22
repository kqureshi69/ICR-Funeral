"""Git-free substitutes for the SDD scripts: this project has no repository."""
import re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(r"C:\ClaudeCode\funeral")
WS = ROOT / ".superpowers/sdd/2026-09-21-grave-owners"
PLAN = ROOT / "docs/superpowers/plans/2026-09-21-grave-owners.md"
# Everything a task may touch. Snapshots of these stand in for commits.
TRACKED = ["graveyard", "tests", "docs", "README.md", "requirements.txt"]


def brief(n: int) -> Path:
    text = PLAN.read_text(encoding="utf-8")
    header = re.search(r"^(# .*?)(?=^### Task )", text, re.S | re.M).group(1)
    blocks = re.split(r"^### Task ", text, flags=re.M)[1:]
    for b in blocks:
        if b.startswith(f"{n}:"):
            out = WS / "briefs" / f"task-{n}-brief.md"
            out.write_text(header + "\n### Task " + b, encoding="utf-8")
            return out
    raise SystemExit(f"no Task {n} in plan")


def snapshot(label: str) -> Path:
    dest = WS / "snapshots" / label
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for item in TRACKED:
        src = ROOT / item
        if not src.exists():
            continue
        target = dest / item
        if src.is_dir():
            shutil.copytree(src, target,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    return dest


def package(base_label: str, name: str) -> Path:
    """A review package: file list + stats + full unified diff, base -> now."""
    base = WS / "snapshots" / base_label
    head = snapshot(f"{name}-head")
    out = WS / "packages" / f"{name}.md"
    r = subprocess.run(["diff", "-ruN", "--exclude=__pycache__", str(base), str(head)],
                       capture_output=True)
    # Decode as UTF-8 explicitly: the Windows locale mangles em dashes into
    # mojibake, which sends reviewers chasing encoding bugs that do not exist.
    diff = r.stdout.decode("utf-8", errors="replace")
    changed, added, removed = set(), 0, 0
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            p = line.split("\t")[0][4:]
            for marker in (str(base), str(head)):
                if p.startswith(marker):
                    rel = p[len(marker):].lstrip(chr(92)+chr(47))
                    if rel:
                        changed.add(rel.replace("\\", "/"))
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    body = [f"# Review package: {name}",
            "",
            "No git in this project: this diff is snapshot-to-snapshot,",
            f"base `{base_label}` -> current working tree.",
            "",
            "## Files changed", ""]
    body += [f"- {c}" for c in sorted(changed)] or ["- (none)"]
    body += ["", f"## Stat", "", f"{len(changed)} files, +{added} / -{removed} lines",
             "", "## Full diff", "", "```diff", diff, "```"]
    out.write_text("\n".join(body), encoding="utf-8")
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "brief":
        print(brief(int(sys.argv[2])))
    elif cmd == "snapshot":
        print(snapshot(sys.argv[2]))
    elif cmd == "package":
        print(package(sys.argv[2], sys.argv[3]))
