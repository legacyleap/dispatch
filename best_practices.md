# Dispatch — intended architecture (for reviewers, human or automated)

Dispatch is a FastAPI + SQLAlchemy + PostgreSQL service. Code is organised **by domain**
(`src/dispatch/<domain>/`), and inside a domain by role:

| File | Role | May import |
|---|---|---|
| `views.py` | HTTP endpoints only: parse request, call `flows`/`service` of **its own domain**, return | its own `flows`, `service`, `models`; shared `dispatch.auth`, `dispatch.database`, `dispatch.common` |
| `flows.py` | orchestration across domains (the only place a domain talks to another domain) | any domain's `service`/`flows`, `plugins` |
| `service.py` | data access and business rules for **one** domain; takes `db_session` | its own `models`, other domains' `models` |
| `models.py` | SQLAlchemy models + Pydantic schemas | other `models`, `dispatch.enums` |

Rules:
1. **A `views.py` never imports another domain's `service`.** Cross-domain work goes through `flows.py`.
2. **Enum values are persisted.** Every `DispatchEnum` value (`dispatch/enums.py`, `<domain>/enums.py`) is stored as a string in PostgreSQL and referenced by the Vue UI and the Slack plugin. Changing a value requires an Alembic data migration under `src/dispatch/database/revisions/tenant/versions/` and a UI change in the same PR.
3. **Model changes ship with a migration.** Adding/removing/renaming a `Column` requires an Alembic revision in the same PR.
4. **Shared query helpers are public API.** `dispatch/database/service.py` (`search_filter_sort_paginate`, filters) is called by every domain's views; behavioural changes there are system-wide.
5. **Permissions are a security surface.** `dispatch/auth/permissions.py` changes need a ticket that names them and a security reviewer.
6. **Cost calculation is intentional.** `incident_cost/service.py` role multipliers reflect a documented policy; changing who counts toward cost is a product decision, not a bug fix.
7. A pull request does what its linked issue asks — no more, no less.
