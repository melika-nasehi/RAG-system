/** The backend's origin, derived from whatever host the browser actually
 *  used to load this app rather than a hardcoded "localhost".
 *
 *  Why this matters: "localhost" and "127.0.0.1" (or a VPN's own virtual
 *  adapter address) are different origins to a browser even when they reach
 *  the same machine. If the frontend is loaded via one and this were
 *  hardcoded to the other, every API call would cross an origin the backend
 *  never authorized in CORS_ALLOWED_ORIGINS — a failure that looks like "the
 *  whole site is broken" but is really just an origin mismatch. Matching
 *  whatever hostname is already in the address bar sidesteps that class of
 *  bug entirely, VPN-changed routing included.
 *
 *  The backend's port is still fixed at 8000 — that part isn't something
 *  the browser's address bar can tell us, and the two dev servers are
 *  always run on the same host by convention.
 */
export const API_BASE = `${location.protocol}//${location.hostname}:8000/api`;
