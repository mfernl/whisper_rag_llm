# 0001 — One issue, branch and pull request per spec, gated by CI

- Status: Accepted
- Date: 2026-11-16
- Constitution: v1.1.0 → v2.0.0 (MAJOR: section 4 branching rule redefined; section 3 gains a CI gate)

## Context
- Constitution v1.1.0 section 4 said "one branch per task". Each spec produces several small tasks, and this is a one-person project with no reviewer, so a branch and pull request per task would add overhead without adding review.
- Constitution section 3 says a task is done only when the whole suite is green, but nothing enforced it: it depended on running the tests by hand.
- CI was planned as the last phase (README/CI), after every other feature had already been built without it.

## Decision
1. **One GitHub issue, one branch and one pull request per spec.** The branch is named like the spec folder (`NNN-name`, the same convention Spec Kit uses for feature branches: https://github.com/github/spec-kit). Inside the branch, one commit per task (unchanged). The pull request description includes `Closes #N` so merging it closes the issue (https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue). This is GitHub flow (https://docs.github.com/en/get-started/using-github/github-flow).
2. **CI with GitHub Actions** runs the test suite on every push and pull request. A pull request is merged only when CI is green.
3. **CI moves to Phase 3**, right after closing Phase 2, so that every later phase is built with it. Continuous deployment to Render stays in the last phase, since there is nothing worth deploying automatically until `/ask` works.

## Consequences
- The roadmap in `specs/000-vision.md` section 6 is renumbered: 3 CI, 4 ingestion, 5 `/ask`, 6 agent, 7 evaluation, 8 worker, 9 README + CD.
- Phase 3 must deal with tests that cannot run on GitHub's CPU-only runners (`tests/test_fastapi.py` uses `torch.cuda`) and add a `requirements-dev.txt` for test-only dependencies.
- Until Phase 3 is done, direct commits to `main` are still allowed.
- Branch-per-spec is our own judgment for a solo project; if collaborators join, revisit branch-per-task or required reviews.
