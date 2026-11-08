# Evidence: cards 45, 46

- #46 merged through the gate with no finding. It stops the `--slurp` with `--jq` pair before any read, with no halt file. This closes the failure that halted card #42's review.
- #45 review round 1 found 2 defects: the new `super-board-qa-log-check.py` was not called by anything (Gap), and a renamed file or a non-ASCII `.log` name passed the check (Bug). Rebuild round 1 fixed both. The second review passed at head f29ea6f with 140 passed.
- #45 stopped at the merge gate with exit 7. The rebuild edited `.agents/skills/super-qa/SKILL.md:84`, which quotes "drop table". The keyword scan matched the added line. It is a false positive, the third one after #7 and #37. A human `done` comment on the issue let PR #48 merge.
- The merge policy `schema` keyword scope (skip `*.log` and `docs/super-board/runs/**`) stays a human-only edit. The new check removes the log cause. Quoted skill text still matches.
- Prior calibration (run 2026-11-08 cards 37, 38, 42) found no lesson and proposed the two cards in this run.
- Offline suite on staging after the last merge: 140 passed.
