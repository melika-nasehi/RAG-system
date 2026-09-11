import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE } from '../shared/api-base';

export interface StudentProfile {
  degree_level: string;
  entry_year: number;
  field_of_study: string;
  is_on_probation: boolean;
  last_semester_gpa: string | null;
}

export interface AuthUser {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
  profile: StudentProfile | null;
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface AuthResponse extends TokenPair {
  user: AuthUser;
}

export interface RegisterPayload {
  username: string;
  password: string;
  email?: string;
  degree_level: string;
  entry_year: number;
  field_of_study?: string;
}

/** Thin HTTP layer for the auth endpoints. State lives in AuthStore; this
 *  just knows the URLs and shapes. */
@Injectable({ providedIn: 'root' })
export class Auth {
  private readonly http = inject(HttpClient);
  private readonly base = `${API_BASE}/auth`;

  register(payload: RegisterPayload): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.base}/register/`, payload);
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.base}/login/`, { username, password });
  }

  /** The backend rotates refresh tokens: the one sent here is invalidated by
   *  this call, and the response carries the replacement the caller must
   *  start using. */
  refresh(refresh: string): Observable<TokenPair> {
    return this.http.post<TokenPair>(`${this.base}/refresh/`, { refresh });
  }

  me(): Observable<AuthUser> {
    return this.http.get<AuthUser>(`${this.base}/me/`);
  }
}
