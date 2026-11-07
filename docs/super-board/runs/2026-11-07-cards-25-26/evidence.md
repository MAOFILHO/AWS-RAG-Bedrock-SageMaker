# Run 2026-11-07-cards-25-26 evidence

- Card #25 (empty question) built, passed QA and Review (111 passed, no findings) on its first round.
- The merge gate stopped it with exit 5: conflict in tests/test_cli.py with staging 85f870c, where card #23 had added --version tests. Cause: #25 branched before #23 merged.
- The Review lane labelled it loop:rebase and moved it to Ready. One rebase pass in wave 3 fixed it. PR #27 then merged at 1578f72 (114 passed, 2 tests fail with the fix removed).
- Card #26 (missing PDF) edits the same file, src/rag_course/cli.py. Preflight blocked it behind #25 with blocked-by: 25. The sweep returned it to Ready when #25 closed.
- Card #26 passed first time. PR #28 merged at 246e0c7 (119 passed).
- No denied command. No human step. No code defect found by Review.
- Lesson candidate: two cards that edit the same test file conflict even when they differ in source file. Preflight sequenced only on the source file.
