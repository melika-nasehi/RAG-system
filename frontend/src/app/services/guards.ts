import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthStore } from '../state/auth-store';

/** Blocks a route until a session is confirmed. Waits for the one-time
 *  startup restore so a valid stored token isn't treated as logged-out. */
export const authGuard: CanActivateFn = async (_route, state) => {
  const store = inject(AuthStore);
  const router = inject(Router);

  await store.ensureRestored();
  if (store.isAuthenticated()) return true;

  return router.createUrlTree(['/login'], { queryParams: { next: state.url } });
};

export const adminGuard: CanActivateFn = async () => {
  const store = inject(AuthStore);
  const router = inject(Router);

  await store.ensureRestored();
  if (store.isAuthenticated() && store.isAdmin()) return true;

  return router.createUrlTree([store.isAuthenticated() ? '/' : '/login']);
};

/** Keeps an already-signed-in user off the login/register pages. */
export const guestGuard: CanActivateFn = async () => {
  const store = inject(AuthStore);
  const router = inject(Router);

  await store.ensureRestored();
  return store.isAuthenticated() ? router.createUrlTree(['/']) : true;
};
