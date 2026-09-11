import { vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { AuthStore } from './auth-store';

const LOGIN = 'http://localhost:8000/api/auth/login/';
const REFRESH = 'http://localhost:8000/api/auth/refresh/';
const ME = 'http://localhost:8000/api/auth/me/';

const USER = { id: 1, username: 'sara', email: '', is_admin: false, profile: null };
const ADMIN = { ...USER, id: 2, username: 'boss', is_admin: true };

describe('AuthStore', () => {
  let store: AuthStore;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        AuthStore,
      ],
    });
    store = TestBed.inject(AuthStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('is unauthenticated with nothing stored', async () => {
    await store.ensureRestored();
    expect(store.isAuthenticated()).toBe(false);
    expect(store.ready()).toBe(true);
  });

  it('stores tokens and user on login', async () => {
    const done = store.login('sara', 'pw');
    http.expectOne(LOGIN).flush({ access: 'a.b.c', refresh: 'r.e.f', user: USER });
    await done;

    expect(store.isAuthenticated()).toBe(true);
    expect(store.accessToken).toBe('a.b.c');
    expect(localStorage.getItem('rag.refresh')).toBe('r.e.f');
  });

  it('reports admin role from the user payload', async () => {
    const done = store.login('boss', 'pw');
    http.expectOne(LOGIN).flush({ access: 'a', refresh: 'r', user: ADMIN });
    await done;
    expect(store.isAdmin()).toBe(true);
  });

  it('clears everything and redirects on logout', async () => {
    const done = store.login('sara', 'pw');
    http.expectOne(LOGIN).flush({ access: 'a', refresh: 'r', user: USER });
    await done;

    const nav = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    store.logout();

    expect(store.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('rag.access')).toBeNull();
    expect(nav).toHaveBeenCalledWith(['/login']);
  });

  it('exchanges a refresh token for a new access+refresh pair (rotation)', async () => {
    const login = store.login('sara', 'pw');
    http.expectOne(LOGIN).flush({ access: 'old', refresh: 'r-old', user: USER });
    await login;

    const refreshed = store.refreshAccess();
    http.expectOne(REFRESH).flush({ access: 'new', refresh: 'r-new' });
    expect(await refreshed).toBe('new');
    expect(store.accessToken).toBe('new');

    // The rotated refresh token must be stored too — the backend has
    // already invalidated 'r-old' by the time this response arrives.
    expect(localStorage.getItem('rag.refresh')).toBe('r-new');
  });

  it('restore() drops a stored token the server no longer accepts', async () => {
    // AuthStore reads storage in its constructor, so seed it before a fresh
    // module builds the instance.
    localStorage.setItem('rag.access', 'stale');
    localStorage.setItem('rag.refresh', 'stale');
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting(), AuthStore],
    });
    const fresh = TestBed.inject(AuthStore);
    const http2 = TestBed.inject(HttpTestingController);

    const done = fresh.ensureRestored();
    http2.expectOne(ME).flush({ detail: 'expired' }, { status: 401, statusText: 'Unauthorized' });
    await done;

    expect(fresh.isAuthenticated()).toBe(false);
    expect(localStorage.getItem('rag.access')).toBeNull();
    http2.verify();
  });
});
