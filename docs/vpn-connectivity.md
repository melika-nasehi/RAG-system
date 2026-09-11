# Why the VPN's tunnel mode blocks reaching the site

## Root cause — found by reproducing the identical symptom, not by inspection

While testing this session, the exact symptom described (site unreachable, dev
server logs say it's running) reproduced in this environment. Diagnosis:

**`ng serve` (Angular's dev server) defaults to binding only the IPv6 loopback
address, `[::1]`, not IPv4 `127.0.0.1`.** Confirmed directly:

```
netstat -ano | findstr :4200
  TCP    [::1]:4200    [::]:0    LISTENING   <pid>      ← only this
```

No `127.0.0.1:4200` line at all. A browser request to `http://localhost:4200`
that resolves `localhost` to `127.0.0.1` gets `ERR_CONNECTION_REFUSED` —
nothing is listening on that address — even though the server is genuinely
running and its own logs claim `http://localhost:4200/`.

**This is exactly what a VPN in tunnel mode does to `localhost` resolution.**
Full-tunnel VPN clients commonly install their own virtual network adapter,
change interface metrics, and frequently disable or reroute IPv6 specifically
(IPv6 tunneling is harder to do correctly, so many VPN clients just turn it
off, or the OS falls back to a route that behaves as if it were off). That
flips which address family `localhost` resolves to first, or which one is
actually routable — turning "the frontend server happens to only be
listening on IPv6" from a latent bug into an active, VPN-state-dependent
outage. Django's dev server has the mirror-image issue: `manage.py
runserver` with no explicit bind address defaults to **IPv4-only**
`127.0.0.1:8000`. Whichever address family the VPN's tunnel mode deprioritizes,
whichever one of the two dev servers was listening only on that family stops
being reachable — independent of anything in the application code.

## Fixes applied

| File | Change |
|---|---|
| [`frontend/package.json`](../frontend/package.json) | `"start": "ng serve --host 0.0.0.0"` — binds all interfaces/both families instead of the ambiguous default. **Verified**: this alone fixed the reproduced outage in this environment. |
| [`.claude/launch.json`](../.claude/launch.json) | Backend entry now runs `manage.py runserver 0.0.0.0:8000` explicitly, for the same reason. **Run it this way** — `python manage.py runserver` with no address still defaults to IPv4-only. |
| [`backend/config/settings.py`](../backend/config/settings.py) | `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` now also read `DJANGO_ALLOWED_HOSTS` / `CORS_EXTRA_ORIGINS` from `.env` (comma-separated) — an escape hatch if the VPN ever makes the browser reach the app via some other hostname/IP (its virtual adapter's own address, say), without needing a code change. Empty by default; `DEBUG=True` already implicitly allows plain `localhost`/`127.0.0.1`/`[::1]`. |
| `frontend/src/app/shared/api-base.ts` (new), used by `rag.ts` / `auth.ts` / `admin.ts` | The API base URL is now derived from `location.hostname` (whatever host the browser actually used to load the app) instead of a hardcoded `'http://localhost:8000'`. Answers your question 2 directly — yes, those were hardcoded. This matters because `localhost` and `127.0.0.1` are different **origins** to a browser even on the same machine; if the frontend were ever reached via one and the API call hardcoded the other, that's a CORS failure layered on top of (or independent of) the connectivity one. |

## Your three questions, answered

1. **Is the Django dev server binding in a way that becomes unreachable under changed local routing?** Yes — by default it's IPv4-loopback-only (`127.0.0.1:8000`), no IPv6. Fixed: run it as `0.0.0.0:8000` (now the default via `.claude/launch.json`; if you run `manage.py runserver` by hand, include the address explicitly).
2. **Hardcoded `localhost`/`127.0.0.1` URLs in Angular?** Yes, in three service files. Fixed — now derived from the page's own origin.
3. **Are `CORS_ALLOWED_ORIGINS` / `ALLOWED_HOSTS` too narrow for a changed network path?** Yes, both were fixed lists with no env override. Fixed — both now extendable via `.env` without touching code.

## What's left as a VPN-client issue, not an app issue

The underlying trigger — the VPN's tunnel mode changing which IP family
`localhost` prefers or disables IPv6 — is the VPN client's behavior, not
something fixable from this codebase. The fix here is architectural: **stop
depending on which family `localhost` happens to resolve to** by having both
dev servers listen on all interfaces. That should make the site reachable
with the VPN in tunnel mode continuously, without toggling it — but if a
specific VPN product reroutes `127.0.0.1` itself somewhere unexpected (rare,
but some enterprise VPN/proxy setups do this), that would be a genuine
"outside the app's control" case; the `DJANGO_ALLOWED_HOSTS` /
`CORS_EXTRA_ORIGINS` escape hatch above is there for exactly that residual
case.

## To verify on your machine

1. Pull these changes, restart both dev servers (`npm start` in `frontend/`,
   `python manage.py runserver 0.0.0.0:8000` in `backend/`).
2. Turn the VPN's tunnel mode on.
3. Load `http://localhost:4200` — should work without toggling the VPN off.

If it still fails, run `netstat -ano | findstr :4200` and `:8000` with the
VPN on and off and compare — that will show directly whether this specific
VPN is doing something beyond the IPv4/IPv6 preference flip (e.g. actually
blocking loopback traffic outright, which would need a VPN-side split-tunnel
exclusion rather than a code change).
