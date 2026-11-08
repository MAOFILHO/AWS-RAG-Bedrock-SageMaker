# Evidence: cards 29, 30, 31, 35

- All 4 cards went build, QA, review with no bounce and no human step.
- Each PR merged to `staging` through `super-board-merge-gate.sh`, pinned to the reviewed head.
- Offline suite on `staging` after the last merge: 129 passed, 25 live deselected.
- First live run: 22 passed, 3 failed. These 3 failures became cards #29, #30 and #31.
- Live rerun after #29, #30 and #31: 23 passed, 2 failed. The artist refusal passed on rerun (flaky). The employee test failed again (test asked for a count the question did not ask for). This became card #35.
- Open review nits: #29 no test asserts wait values and `core.py:102` raises `AttributeError` if a response is None. #31 stub test depends on exact prompt wording.
- Shared-file note: no card in this run conflicted with another.
