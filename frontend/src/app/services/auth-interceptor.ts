import { HttpErrorResponse, HttpHandlerFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, from, switchMap, throwError } from 'rxjs';
import { AuthStore } from '../state/auth-store';

const AUTH_PATHS = ['/api/auth/login/', '/api/auth/register/', '/api/auth/refresh/'];

// Shared so a burst of parallel 401s triggers exactly one refresh.
let refreshing: Promise<string | null> | null = null;

/** Attaches the bearer token, and on a 401 refreshes once and retries the
 *  original request. A failed refresh logs the session out. */
export function authInterceptor(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
): Observable<import('@angular/common/http').HttpEvent<unknown>> {
  const store = inject(AuthStore);

  if (AUTH_PATHS.some((path) => req.url.includes(path))) {
    return next(req);
  }

  const withToken = (token: string | null) =>
    token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(withToken(store.accessToken)).pipe(
    catchError((error: unknown) => {
      if (!(error instanceof HttpErrorResponse) || error.status !== 401 || !store.accessToken) {
        return throwError(() => error);
      }

      refreshing ??= store.refreshAccess().finally(() => {
        refreshing = null;
      });

      return from(refreshing).pipe(
        switchMap((fresh) => {
          if (!fresh) {
            store.logout();
            return throwError(() => error);
          }
          return next(withToken(fresh));
        }),
      );
    }),
  );
}
