"""
publish_students.py - copy the course to the student repo (what participants clone in Colab).

Two repos:
  team repo     - where the team works: branches `solutions` and `main`, plus internal docs
  student repo  - the same two branches WITHOUT the internal files listed in INTERNAL below

Usage (in the team repo, on `solutions`, everything committed, after `python scripts/make_main.py`):
    python scripts/publish_students.py <student repo URL>   # first time: saves the URL as remote "students"
    python scripts/publish_students.py                      # every later update

Each run adds one commit to each student branch, made by a neutral author (no personal email).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERNAL = ("HANDOVER.md", "docs/handover/", "docs/s5_instructor_notes.md", "docs/dry_run_log_template.md")
AUTHOR = ["-c", "user.name=Tuwaiq Workshop", "-c", "user.email=workshop@tuwaiq.invalid"]


def git(*args, cwd=ROOT):
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.decode(errors='replace')}")
    return result.stdout.decode("utf-8", errors="replace")


def student_files(branch):
    """{path: bytes} of a team branch, without the internal files."""
    paths = [p for p in git("ls-tree", "-r", "--name-only", "-z", branch).split("\0") if p]
    return {p: subprocess.run(["git", "show", f"{branch}:{p}"], cwd=ROOT, capture_output=True, check=True).stdout
            for p in paths if not p.startswith(INTERNAL)}


def publish(branch, team_sha):
    local = f"students-{branch}"  # local copy of the student branch
    on_remote = git("ls-remote", "--heads", "students", branch).strip()
    if on_remote:
        git("fetch", "--quiet", "students", f"+{branch}:{local}")
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / branch
        if on_remote:
            git("worktree", "add", "--quiet", str(tree), local)
        else:
            git("worktree", "add", "--quiet", "--orphan", "-b", local, str(tree))
        try:
            for path in [p for p in git("ls-files", "-z", cwd=tree).split("\0") if p]:
                (tree / path).unlink()
            for path, data in student_files(branch).items():
                (tree / path).parent.mkdir(parents=True, exist_ok=True)
                (tree / path).write_bytes(data)
            git("add", "--all", cwd=tree)
            if git("status", "--porcelain", cwd=tree).strip():
                git(*AUTHOR, "commit", "--quiet", "-m", f"Update from team repo ({team_sha})", cwd=tree)
            git("push", "--quiet", "students", f"{local}:{branch}")
            print(f"students/{branch}: {git('log', '-1', '--format=%h %s', local).strip()}")
        finally:
            git("worktree", "remove", "--force", str(tree))


def main():
    if len(sys.argv) > 1:  # first time: remember the student repo URL
        if "students" in git("remote").split():
            git("remote", "set-url", "students", sys.argv[1])
        else:
            git("remote", "add", "students", sys.argv[1])
    if "students" not in git("remote").split():
        sys.exit("Give the student repo URL the first time: python scripts/publish_students.py <URL>")
    if git("status", "--porcelain").strip():
        sys.exit("Commit (or stash) your changes first.")
    team_sha = git("rev-parse", "--short", "solutions").strip()
    for branch in ("main", "solutions"):  # main first: GitHub makes the first pushed branch the default
        publish(branch, team_sha)


if __name__ == "__main__":
    main()
