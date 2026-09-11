import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { Auth, type AuthUser, type RegisterPayload } from '../services/auth';

const ACCESS_KEY = 'rag.access';
const REFRESH_KEY = 'rag.refresh';

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage disabled — session stays in memory only */
  }
}

/** Owns the session: tokens (persisted to localStorage), the current user,
 *  and the sign-in / sign-out transitions. The interceptor reads the access
 *  token from here and calls `refreshAccess()` / `logout()`. */
@Injectable({ providedIn: 'root' })
export class AuthStore {
  private readonly api = inject(Auth);
  private readonly router = inject(Router);

  private readonly _access = signal<string | null>(read(ACCESS_KEY));
  private readonly _refresh = signal<string | null>(read(REFRESH_KEY));
  private readonly _user = signal<AuthUser | null>(null);
  private readonly _ready = signal(false);

  readonly user = this._user.asReadonly();
  readonly ready = this._ready.asReadonly();
  readonly isAuthenticated = computed(() => !!this._access() && !!this._user());
  readonly isAdmin = computed(() => !!this._user()?.is_admin);

  private restoring: Promise<void> | null = null;

  get accessToken(): string | null {
    return this._access();
  }

  /** Runs once, however many callers await it: if a token is stored, confirm
   *  it still resolves to a user. Clears a dead session silently. Both the
   *  app-startup effect and the route guards go through here. */
  ensureRestored(): Promise<void> {
    return (this.restoring ??= this.restore());
  }

  private async restore(): Promise<void> {
    if (this._access()) {
      try {
        this._user.set(await firstValueFrom(this.api.me()));
      } catch {
        this.clear();
      }
    }
    this._ready.set(true);
  }

  async login(username: string, password: string): Promise<void> {
    const res = await firstValueFrom(this.api.login(username, password));
    this.accept(res.access, res.refresh, res.user);
  }

  async register(payload: RegisterPayload): Promise<void> {
    const res = await firstValueFrom(this.api.register(payload));
    this.accept(res.access, res.refresh, res.user);
  }

  /** Used by the interceptor on a 401. Returns the new access token, or null
   *  if the refresh token is also dead (caller should then log out).
   *
   *  The backend rotates refresh tokens on every use — the one just spent
   *  stops working from this call on — so the replacement it returns has to
   *  be stored too, not just the access token. Losing that write would mean
   *  the *next* refresh silently fails with a session that looked fine. */
  async refreshAccess(): Promise<string | null> {
    const refresh = this._refresh();
    if (!refresh) return null;
    try {
      const res = await firstValueFrom(this.api.refresh(refresh));
      this._access.set(res.access);
      this._refresh.set(res.refresh);
      write(ACCESS_KEY, res.access);
      write(REFRESH_KEY, res.refresh);
      return res.access;
    } catch {
      return null;
    }
  }

  logout(redirect = true): void {
    this.clear();
    if (redirect) this.router.navigate(['/login']);
  }

  private accept(access: string, refresh: string, user: AuthUser): void {
    this._access.set(access);
    this._refresh.set(refresh);
    this._user.set(user);
    write(ACCESS_KEY, access);
    write(REFRESH_KEY, refresh);
  }

  private clear(): void {
    this._access.set(null);
    this._refresh.set(null);
    this._user.set(null);
    write(ACCESS_KEY, null);
    write(REFRESH_KEY, null);
  }
}
