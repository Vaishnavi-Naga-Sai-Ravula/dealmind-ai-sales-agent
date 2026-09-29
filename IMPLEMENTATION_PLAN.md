# DealMind implementation plan

Repository inspection (2026-09-29): the tracked skeleton has been partially filled
with uncommitted FastAPI, SQLite, Hindsight adapter, React dashboard and sample data
files. Preserve and verify that work. README.md and .env.example are empty; tests
and screenshots contain only empty .gitkeep placeholders. No AGENTS.md was found.
The existing virtual environment contains hindsight-client 0.10.1. No Hindsight
environment configuration is present. Preserve the original directory structure.

1. Foundation: validated Pydantic models, environment settings, SQLite repository,
   realistic sample data; compile and check persistence.
2. Memory: official Hindsight async SDK adapter, separate bank per deal, stable
   document IDs, synchronous ingestion completion, explicit failure status and retry.
3. Workflows: deal list/detail/create, interaction create, memory sync and recall.
4. Intelligence: recall first, then Hindsight reflect with current deal and recalled
   evidence; isolated service and transparent deterministic fallback.
5. React + Vite dashboard: customer navigation, interaction capture/history, memory
   evidence, intelligence, loading/error/empty states, responsive layout.
6. Verification: API tests with injected external-service doubles; SDK contract tests;
   opt-in live Hindsight smoke test; frontend production build and browser checks.
7. Documentation: configuration, run commands, architecture, endpoints, demo scenario,
   verified results and credential-dependent limitations.

Design constraints: SQLite is business data, never a pretend Hindsight memory store.
Without a configured Hindsight service, retain remains pending/failed and recall
reports unavailable. Demo briefs are explicitly rules-based. No secrets in source.
This is a local single-user MVP; authentication/multi-tenant deployment is out of scope.

Sources verified: https://hindsight.vectorize.io/sdks/python,
https://hindsight.vectorize.io/developer/api/retain,
https://hindsight.vectorize.io/developer/api/recall.
The supplied PDFs are reference context; their article/social publishing prompts are
not tasks requested for this implementation.
