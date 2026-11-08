# Run 2026-11-07 aws-rag-bedrock-sagemaker

| Card | Lanes | Final | Column | Detail |
|---|---|---|---|---|
| #7 | build:advanced → qa:advanced → review:human-gate | human-gate | Blocked | Review clean (86 passed). Merge gate exit 7: keyword "drop table" in tests/golden/destructive_sql.json fixture. Needs human. PR #21 |
| #11 | build:advanced → qa:advanced → review:bounced | bounced | QA | Review→QA: prompt-leak injection test cannot fail (tests/test_safety.py:69), AC1 proven 4/5. PR #20 |
| #11 | qa:failed | failed | QA | Fixed R1/R2 in tests/test_safety.py, pushed 82064fe (71 passed). GitHub writes denied by permission classifier: thread, PR #20 blocks, [qa] comments, move to Review not done. |
| #11 | qa:failed | failed | QA | QA v2 re-check passed (71 tests, mutations red, security 0 issues); pushed 2e6a2a3, PR blocks updated. Classifier denied reply to thread 4502125264 and resolve of PRRT_kwDOVkjmOs602_xi; card stays in QA. |
| #11 | review:failed | failed | Review | Review passed (71 tests, R1/R2 fixed, truth-check 88/90, mergeState CLEAN, head 1b758d2). Classifier blocked gh pr ready 20; merge gate not run. |
| #11 | review:halted | halted | Review | Wave 4: QA advanced, Review halted by a false GitHub halt (gh pr checks exits 1, PR has 0 CI checks). Cleared with --resume. |
| #11 | merged | done | Done | PR #20 merged to staging 387ff1a after human done approval. Issue closed, card moved to Done. |
| #7 | merged | done | Done | PR #21 merged to staging 1530f65 after human done approval (drop table false positive). Issue closed, card moved to Done. |
| #25 | build:advanced → qa:advanced → review:bounced | bounced | Ready | Review clean (111 passed, no findings). Merge gate exit 5: conflict in tests/test_cli.py with staging 85f870c (--version tests). Labelled loop:rebase, back to Build for a rebase pass. PR #27. |
| #25 | merged | done | Done | Rebase pass. PR #27 merged to staging 1578f72 through the gate (exit 0). 114 passed with AWS cut off. Truth check 95. No human step. |
| #26 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #28 merged to staging 246e0c7 through the gate, pinned to head d1f275a. 119 passed with AWS cleared. Truth check 92. No findings, no human step. |
| #29 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #33 merged to staging 4b5319b through the gate, pinned to head 69f1a0a. 123 passed with AWS cleared. Truth check 90. Open nits: no test asserts wait values; core.py:102 AttributeError if response is None. |
| #30 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #32 merged to staging e6f59af through the gate. 123 passed. Truth check 95. |
| #31 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #34 merged to staging 0512130 through the gate, pinned to head 50fa57a. 120 passed offline. Live total-sales golden passed. Open nit: stub test depends on exact prompt wording. |
| #35 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #36 merged to staging 0b8ac83 through the gate, pinned to head baa9e8e. 129 passed offline. No findings, no human step. |
| #37 | build:advanced → qa:advanced → review:human-gate | human-gate | Blocked | Review clean (131 passed, 2 mutants red, truth check 90). Merge gate exit 7: keyword "drop table" matches test names in a committed QA pytest.log, not code. Needs human done. PR #39 |
| #37 | merged | done | Done | PR #39 merged to staging 8a3952c after human done approval (drop table false positive from QA pytest.log test names). Issue closed, card moved to Done. |
| #38 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #40 merged to staging 114527c through the gate, pinned to head 654df85. 129 passed offline. No findings, no human step. |
| #42 | build:advanced → qa:advanced → review:halted → review:failed → review:advanced | merged | Done | PR #43 merged to staging 2b6b6cd through the gate, pinned to head 1c5b496. 133 passed offline, live albums golden 5 of 5, live SQL 6 of 6. Truth check 90. Review halted once on a self-caused gh read (--slurp --jq), cleared with --resume, then an agent died when the laptop slept; third review passed. |
| #46 | build:advanced → qa:advanced → review:advanced | merged | Done | PR #47 merged to staging 9e4b571 through the gate, pinned to head 6e729f1. 137 passed offline. Truth check 90. Open nit: the -q form has no test. |
| #45 | build:advanced → qa:advanced → review:bounced | bounced | Ready | Review round 1: nothing calls super-board-qa-log-check.py (Gap), renamed file and non-ASCII .log name pass (Bug). 138 passed. PR #48. |
| #45 | build:advanced → qa:advanced → review:human-gate | human-gate | Blocked | Rebuild round 1 fixed R1 and R2. 140 passed, truth check 90. Merge gate exit 7: keyword "drop table" in an added line, because super-qa/SKILL.md:84 quotes the phrase. Needs human done. PR #48. |
| #26 | preflight:blocked | blocked | Blocked | Same file (src/rag_course/cli.py) as #25. Sequenced behind #25 with blocked-by: 25. Sweep returns it to Ready when #25 closes. |
| #23 | build:advanced → qa:advanced → review:advanced | merged | Done | Unattended test wave. PR #24 merged to staging 85f870c through the merge gate, pinned to head 84a0beb. 114 passed with AWS removed. Truth check 93/100. No human step. |
