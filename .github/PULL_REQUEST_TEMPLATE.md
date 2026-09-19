## Summary

What does this PR change, and why?

## Related issue

Closes #

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactor / cleanup
- [ ] Other (describe):

## How was this tested?

CI runs the non-LLM part of `pytest` automatically, but that's not a
substitute for describing what you actually ran (see `CONTRIBUTING.md`):

- [ ] Ran `pytest -v` locally (with `LLM_API_KEY` set, if possible, to also
      exercise the LLM-dependent tests that CI skips)
- [ ] Ran `uvicorn main:app --reload` and manually tested the affected flow
      (the frontend has no automated test coverage)
- [ ] Ran `evaluate.py` and checked for retrieval/answer regressions
      (if this PR touches chunking, retrieval, or the prompt)
- [ ] Other (describe):

## Checklist

- [ ] I've read `CONTRIBUTING.md`
- [ ] I updated relevant documentation (`README.md` / `ARCHITECTURE.md` /
      `DECISIONS.md`) if this changes user-facing behavior or a design
      decision
- [ ] I did not commit `.env`, an API key, or any other secret
- [ ] This PR is focused on one concern
