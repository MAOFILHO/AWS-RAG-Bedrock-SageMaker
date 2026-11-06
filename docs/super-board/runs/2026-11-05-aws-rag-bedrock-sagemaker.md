# Run manifest aws-rag-bedrock-sagemaker

| Card | Lanes | Final | Column | Detail |
|---|---|---|---|---|
| #2 | build:advanced → qa:advanced → review:advanced | advanced | Done | PR #13 merged, 20b6ca1 on staging |
| #3 | build:advanced → qa:advanced → review:advanced | advanced | Done | PR #14 merged, 7c145ea on staging |
| #4 | build:advanced → qa:advanced → review:human-gate | human-gate | Blocked | PR #15 review passed, 434 lines over the 400 limit, needs human merge |
| #4 | human merge | merged | Done | PR #15 merged by owner, 4e94d00 on staging |
| #5 | qa:advanced → review:advanced | advanced | Done | PR #18 merged, 0be10c8 on staging |
| #6 | review:human-gate | human-gate | Blocked | PR #17 review passed, merge gate schema keyword "drop table" in test prompts |
| #9 | review:bounced | bounced | Ready | AC1 fails with LANGSMITH_TRACING=true and no key, loop:rebuild-1 |
