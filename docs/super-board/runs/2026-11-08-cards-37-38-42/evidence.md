# Evidence: cards 37, 38, 42

- #37 and #38 ran in one wave. #37 stopped at the merge gate with exit 7 (human gate) on the keyword "drop table". The match was test names in the committed QA `pytest.log`. A human `done` comment on the issue let the PR merge.
- #38 merged through the gate with no finding.
- #42 review halted once (exit 79). The review agent ran `gh api ... --paginate --slurp --jq .` against PR comments. gh rejected the flag pair 3 times and the helper wrote `github-halt.json`. No GitHub writes happened. A bare `gh api` read worked. The halt was cleared with `super-board-github-read.py --resume`. Cost: one extra relaunch.
- The second #42 review agent failed with "computer went to sleep mid-response". No result, no writes. A third review passed and merged through the gate.
- Prior calibration (run 2026-11-07 cards 29, 30, 31, 35) found no lesson. This run adds two events: a forbidden gh flag pair in a review lane, and a QA log in a PR that trips the schema keyword gate.
- Offline suite on staging after the last merge: 133 passed.
