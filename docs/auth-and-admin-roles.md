# Authentication, roles, and admin document upload (Part 4)

## Summary

- Real JWT auth replaces the hard-coded `get_test_user()`. Every API endpoint
  now requires an authenticated user; conversations are scoped to `request.user`.
- Two roles, keyed on Django's built-in `is_staff`: **student** (has a
  `StudentProfile`, asks questions) and **admin** (`is_staff=True`, manages the
  corpus). No new model field.
- The offline ingest pipeline (validate → chunk → embed → index) is now
  importable `core/` code. An admin-only endpoint runs an uploaded PDF through
  the *same* pipeline; a file that fails validation is rejected with a reason
  and never indexed.
- Angular gains login/register pages, a JWT interceptor with silent refresh, and
  route guards. Admins additionally see a document-upload page.

> **Note on the JWT library.** PyPI was unreachable in this environment, so
> `djangorestframework-simplejwt` could not be installed. `accounts/tokens.py`
> is a small hand-rolled HS256 implementation with the same on-the-wire format
> and the same access/refresh split. Swapping to simplejwt later is a settings
> change — the endpoints, token shape, and frontend are already compatible.
> See [`backend/requirements.txt`](../backend/requirements.txt).

## Backend

| File | Purpose |
|---|---|
| [`accounts/tokens.py`](../backend/accounts/tokens.py) | HS256 encode/decode, `for_user()`, `access_from_refresh()`. `exp` + `typ` enforced; `hmac.compare_digest` for the signature. Access 30 min, refresh 7 days. |
| [`accounts/authentication.py`](../backend/accounts/authentication.py) | `JWTAuthentication(BaseAuthentication)` — `Authorization: Bearer <access>`. |
| [`accounts/serializers.py`](../backend/accounts/serializers.py) | `RegisterSerializer` creates `User` + `StudentProfile` in one transaction (password run through Django validators). `UserSerializer` exposes `is_admin` and nested `profile`. |
| [`accounts/views.py`](../backend/accounts/views.py) | `register/`, `login/`, `refresh/`, `me/` (GET + PATCH profile). |
| [`api/views.py`](../backend/api/views.py) | `get_test_user()` deleted. `ask` / `conversations` use `request.user`, `IsAuthenticated`. |
| [`api/admin_views.py`](../backend/api/admin_views.py) | `DocumentUploadView`, `IsAdminUser`. `GET` lists corpus documents; `POST` validates an uploaded PDF, and on acceptance saves it to `data/raw/` and calls `ingest_pdf`. |
| [`config/settings.py`](../backend/config/settings.py) | DRF defaults: `JWTAuthentication`, `IsAuthenticated`. |

### Endpoints

```
POST /api/auth/register/   {username, password, email?, degree_level, entry_year, field_of_study?}
                           → 201 {user, access, refresh}
POST /api/auth/login/      {username, password} → 200 {user, access, refresh} | 401
POST /api/auth/refresh/    {refresh} → 200 {access} | 401
GET  /api/auth/me/         → 200 {id, username, email, is_admin, profile}
PATCH /api/auth/me/        {…profile fields} → 200 user

POST /api/ask/             (auth) unchanged shape
GET  /api/conversations/   (auth) — only the caller's
GET  /api/conversations/<id>/ (auth, 404 if not the caller's)

GET  /api/admin/documents/ (admin) → [{source, chunks}]
POST /api/admin/documents/ (admin, multipart `file`)
     → 201 {accepted:true, source, chunks_added, chunks_total, digits_repaired}
     → 400 {accepted:false, source, reason, verdict}   (validation failure or non-PDF)
     → 403 for a student, 401 for anonymous
```

## Ingest pipeline in `core/` (ported from `src/`)

| Module | From | Function |
|---|---|---|
| [`core/ingestion/validation.py`](../core/ingestion/validation.py) | `src/1_data_validation/inspect_data.py` | `validate_pdf(path) → ValidationResult(accepted, verdict, reason, stats)`. Same calibrated thresholds: chars/page ≥ 100, garbage-token ratio ≤ 1%, real-Persian-word ratio ≥ 50%. `REPAIR` (reversed words) counts as accepted. |
| [`core/ingestion/chunking.py`](../core/ingestion/chunking.py) | `src/2_chunking/chunk_documents.py` | `chunk_pdf(path, size, overlap, source_name)` → chunk records. Per-document digit-reversal repair (date-parse test), hazm normalisation, recursive splitter, `MIN_CHUNK_LENGTH=100`. Chunk-id format matches the existing files exactly. |
| [`core/indexing/build_index.py`](../core/indexing/build_index.py) | `src/3_embedding/build_index.py` | `add_chunks(chunks, collection) → n added`. Idempotent — skips ids already in Chroma. |
| [`core/ingestion/pipeline.py`](../core/ingestion/pipeline.py) | new | `ingest_pdf(path, collection) → IngestResult`. validate → chunk (at the collection's size/overlap, parsed from its name) → `add_chunks` → append to `data/chunks/<collection>.jsonl`. Touching the chunk file makes `SparseIndex` rebuild the BM25 index on the next query — no explicit invalidation. |

The endpoint's ingest call is **synchronous**: embedding every chunk through
Ollama takes tens of seconds for a large PDF. Acceptable for a low-frequency
admin action; a background worker is a later concern.

## Frontend

| File | Purpose |
|---|---|
| [`services/auth.ts`](../frontend/src/app/services/auth.ts) | HTTP for the auth endpoints. |
| [`state/auth-store.ts`](../frontend/src/app/state/auth-store.ts) | Session signals; tokens persisted to `localStorage` (wrapped in try/catch). `ensureRestored()` runs once at startup and confirms a stored token still resolves. `refreshAccess()` / `logout()` for the interceptor. |
| [`services/auth-interceptor.ts`](../frontend/src/app/services/auth-interceptor.ts) | Attaches `Bearer`; on a 401 refreshes **once** (shared in-flight promise for parallel 401s) and retries; a dead refresh → `logout()`. Skips the auth endpoints. |
| [`services/guards.ts`](../frontend/src/app/services/guards.ts) | `authGuard` (+ `?next=`), `adminGuard`, `guestGuard`. All await `ensureRestored()` so a valid stored token is never treated as logged-out. |
| [`app.routes.ts`](../frontend/src/app/app.routes.ts) | `/` (chat, `authGuard`), `/login`, `/register` (`guestGuard`), `/admin/documents` (`adminGuard`). All lazy-loaded. |
| [`app.ts`](../frontend/src/app/app.ts) | Now a shell: `<router-outlet>` + a splash until the session is restored. The chat UI moved to [`pages/chat-page/`](../frontend/src/app/pages/chat-page/). |
| [`pages/login-page/`](../frontend/src/app/pages/login-page/), [`pages/register-page/`](../frontend/src/app/pages/register-page/) | Forms, shared card styling. |
| [`pages/admin-documents-page/`](../frontend/src/app/pages/admin-documents-page/) | Corpus list + file picker + upload; renders accepted (chunk count) / rejected (reason). |
| [`components/sidebar/sidebar.ts`](../frontend/src/app/components/sidebar/sidebar.ts) | Account block: username, `مدیر` badge, "مدیریت اسناد" link (admin only), logout. |

## Tests

| Suite | Count | Covers |
|---|---:|---|
| `backend/accounts/tests.py` | 12 | register creates profile; duplicate/weak password rejected & no user left behind; login good/bad; refresh issues access; **an access token is not accepted as a refresh token**; `me` needs auth; profile PATCH; **tampered token rejected** |
| `backend/api/tests.py` | 8 | ask/conversations need auth (401); ask uses `request.user`; a user sees only their own conversations; **student → admin endpoint → 403**; anonymous → 401; **corrupted PDF → 400 with reason, `ingest_pdf` never called**; non-PDF extension rejected; accepted PDF is ingested |
| `tests/test_ingestion.py` (core) | 8 | accepts a real regulation PDF; rejects non-PDF / empty; `collection_params`; chunk record shape & id format; `source_name` override; **pipeline rejects before indexing**; pipeline indexes + appends, and re-run doesn't duplicate |
| `frontend .../auth-store.spec.ts` | 6 | unauthenticated by default; login stores tokens+user; admin role; logout clears + redirects; refresh exchange; `restore()` drops a stale token on 401 |

All green: **core 50, backend 20, frontend 27.**

## End-to-end smoke test (against a live server)

```
register student           → 201, profile created, tokens returned
GET /api/auth/me/ + token   → 200 with profile
GET /api/conversations/ no token   → 401
GET /api/conversations/ + token    → 200 []
GET /api/admin/documents/ as student → 403
POST /api/auth/refresh/            → 200 new access
admin login → GET /api/admin/documents/ → 200, 11 documents listed
admin POST corrupt.pdf → 400 {"accepted":false,"reason":"unreadable PDF: …","verdict":"REJECT"}
```

## Follow-ups / not done

- Ingest is synchronous; large uploads block the request ~30–60 s.
- No token blacklist / logout-server-side (stateless HS256); a stolen access token is valid until `exp` (30 min).
- `SECRET_KEY` in `settings.py` is the dev placeholder — must move to an env var before any real deployment (pre-existing).
- Admin users are created via `createsuperuser` or the Django admin; there is no "promote to admin" API.
