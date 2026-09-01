# Mutation Testing

Mutation testing targets `apps/api-gateway/app/core/token_service.py`, where JWT behavior has fast, deterministic unit tests.

```bash
python -m pip install -r apps/api-gateway/requirements-test.txt
cd apps/api-gateway
mutmut run
mutmut results
```

A surviving mutant is treated as missing test behavior, not merely a coverage number. Add a focused test that fails for the mutant, then rerun the suite. Mutation testing is intentionally kept separate from the regular pull-request workflow because it is computationally expensive.
