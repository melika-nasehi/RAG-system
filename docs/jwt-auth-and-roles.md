# JWT authentication & admin/student roles

## Goal

Replace the hardcoded `get_test_user()` with real authentication, add an
admin role that can grow the document corpus through the app instead of the
offline scripts, and keep everyone else scoped to their own conversations.

## Role model

No new field. **`is_staff`** (Django's own) is admin; everyone else is a
student. `StudentProfile` is created at registration and only students get
one — an admin account manages the corpus, it doesn't ask questions as a
student. `UserSerializer.is_admin` exposes `is_staff` read-only so the
frontend can gate the upload UI without re-deriving the rule.

## JWT — djangorestframework-simplejwt

First attempt: PyPI was unreachable in this environment, so
[`backend/accounts/tokens.py`](../backend/accounts/tokens.py) started as a
~100-line hand-rolled HS256 implementation, built to the exact token shape
simplejwt would produce so swapping the library in later would be a settings
change, not an API change. PyPI access came back later in the project;
`djangorestframework-simplejwt` is now the real dependency, and `tokens.py`
is a thin adapter over it — **no cryptography of its own left**. Verified,
not assumed:

| Property | Verified as |
|---|---|
| Signature checked every request | `AccessToken(tampered)` → `TokenError: Token is invalid` |
| Expiry enforced | An expired token → `ExpiredTokenError: Token is expired` |
| Algorithm pinned server-side | `SIMPLE_JWT["ALGORITHM"]="HS256"` explicit in settings; the library always calls `jwt.decode(..., algorithms=[self.algorithm])` — never reads an algorithm from the token itself, which rules out "alg:none"/algorithm-confusion as a class |
| Refresh rotation | **On** — see below |

`backend/accounts/authentication.py` (the old hand-rolled DRF backend) is
gone; `settings.py` points at `rest_framework_simplejwt.authentication.JWTAuthentication`
directly.

### Refresh token rotation

`SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] = True` and `BLACKLIST_AFTER_ROTATION =
True`, backed by the `rest_framework_simplejwt.token_blacklist` app
(migrated). `accounts.tokens.rotate_refresh()` — called from `RefreshView` —
blacklists the refresh token it's given and returns a **new** access/refresh
pair; the old refresh token is rejected on any later attempt, from either
the legitimate client or whoever else might have a copy of it. The response
shape of `POST /api/auth/refresh/` changed from `{"access"}` to
`{"access", "refresh"}` accordingly — the Angular `AuthStore.refreshAccess()`
stores both now, not just the access token, since the one it sent is dead
the moment the response comes back.

Tested: `test_refresh_rotates_and_returns_a_new_refresh_token`,
`test_a_refresh_token_cannot_be_reused_after_rotation` (the reuse case —
old token → 200 once, 401 the second time), `test_the_rotated_refresh_token_itself_works`
(rotation chains, not a dead end) in `backend/accounts/tests.py`.

## What was built

**Backend**
| File | Role |
|---|---|
| [`backend/accounts/tokens.py`](../backend/accounts/tokens.py) | `for_user()` / `rotate_refresh()` / `decode()` — thin adapter over simplejwt |
| [`backend/accounts/serializers.py`](../backend/accounts/serializers.py) | `RegisterSerializer` (user + profile, atomic), `UserSerializer`, `StudentProfileSerializer` |
| [`backend/accounts/views.py`](../backend/accounts/views.py) + [`urls.py`](../backend/accounts/urls.py) | `POST /api/auth/register/`, `/login/`, `/refresh/` (rotates), `GET/PATCH /api/auth/me/` |
| [`backend/api/views.py`](../backend/api/views.py) | `get_test_user()` removed; `ask`/`conversations`/`conversation-detail` now `IsAuthenticated`, scoped to `request.user`; 404 via `get_object_or_404` (previously an unhandled `DoesNotExist`) |
| [`backend/api/admin_views.py`](../backend/api/admin_views.py) | `DocumentUploadView` — `IsAdminUser`; `GET` lists indexed sources, `POST` validates → ingests a PDF |
| [`backend/config/settings.py`](../backend/config/settings.py) | `rest_framework_simplejwt.authentication.JWTAuthentication` default; `DEFAULT_PERMISSION_CLASSES=[IsAuthenticated]`; `SIMPLE_JWT` config; `.env`-backed `DATABASES` |

**Ingestion pipeline — ported from `src/` into `core/` so the admin endpoint and the offline scripts call the same code**
| File | Ported from |
|---|---|
| [`core/ingestion/validation.py`](../core/ingestion/validation.py) | `src/1_data_validation/inspect_data.py` — same calibrated thresholds |
| [`core/ingestion/chunking.py`](../core/ingestion/chunking.py) | `src/2_chunking/chunk_documents.py` — same chunk id/record shape |
| [`core/indexing/build_index.py`](../core/indexing/build_index.py) | `src/3_embedding/build_index.py`, trimmed to `add_chunks()` |
| [`core/ingestion/pipeline.py`](../core/ingestion/pipeline.py) | New — `ingest_pdf()`: validate → chunk → embed → append to the chunk file (so `SparseIndex` picks it up via its normal staleness check, no explicit cache-bust needed) |

**Frontend**
| File | Role |
|---|---|
| `state/auth-store.ts` | Session signals, localStorage persistence, `ensureRestored()` (one-time, shared across guards and app startup), `refreshAccess()` |
| `services/auth.ts`, `services/admin.ts` | HTTP layer for auth and document endpoints |
| `services/auth-interceptor.ts` | Attaches `Bearer`; on 401, de-duplicated single refresh-then-retry, logs out on refresh failure |
| `services/guards.ts` | `authGuard`, `adminGuard`, `guestGuard` |
| `pages/login-page`, `pages/register-page`, `pages/admin-documents-page` | New routes |
| `app.routes.ts` | `chat-page` (auth), `login`/`register` (guest-only), `admin/documents` (admin-only) |

## Tests

**Backend (Django) — 23 passing**, including exactly what was asked:
- `test_student_cannot_reach_the_admin_endpoint` — 403 on both GET and POST
- `test_unauthenticated_request_is_401_not_403` — the two are distinguished
- `test_a_corrupted_pdf_is_rejected_with_a_reason_and_never_indexed` — `ingest_pdf` asserted **not called**
- `test_a_refresh_token_cannot_be_reused_after_rotation`, `test_the_rotated_refresh_token_itself_works`
- Plus: register creates user + profile atomically, duplicate username, weak password, login/tampered-token rejection, a user only sees their own conversations, `ask` uses `request.user` not a shared test user, accepted-PDF end-to-end (mocked ingest).

**Core — new `tests/test_ingestion.py`**, part of the 50 passing `pytest` suite: validation accept/reject/repair on real calibration PDFs, chunking id/shape, pipeline orchestration with a fake indexer.

**Frontend — 27 passing** (`vitest`), covering the existing components plus the new auth/admin surface.

## Result

All auth and role-gating requirements met and tested. `core/` still has no Django import — the admin view calls `core.ingestion.pipeline` and `core.ingestion.validation` the same way a future CLI script would.
