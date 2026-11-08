#!/usr/bin/env python3
"""Fail when a PR diff adds a *.log file outside docs/super-board/runs/.

QA logs in the diff trip the merge gate's keyword scan (exit 7). Post logs as an
issue comment or keep them outside the repo.

Usage: super-board-qa-log-check.py --base <ref> [--head HEAD] [--repo .]
Exit 0 clean, 1 log file found, 2 git failed.
"""
import argparse
import subprocess
import sys

ALLOWED_PREFIX = "docs/super-board/runs/"


def offending(paths):
    return [p for p in paths if p.endswith(".log") and not p.startswith(ALLOWED_PREFIX)]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args(argv)
    res = subprocess.run(
        ["git", "-C", args.repo, "diff", "--name-only", "--diff-filter=A", f"{args.base}...{args.head}"],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(res.stderr.strip(), file=sys.stderr)
        return 2
    bad = offending(res.stdout.splitlines())
    for path in bad:
        print(f"QA log added to the PR diff: {path}. Remove it (git rm) and post the log as an issue comment instead.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
