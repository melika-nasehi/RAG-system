import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { API_BASE } from '../shared/api-base';

export interface RagAnswer {
  conversation_id: number;
  question: string;
  answer: string;
  sources: string[];
  backend: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources: string[];
}

export interface ConversationDetail {
  id: number;
  title: string;
  messages: Message[];
}

/** A single, already-localised error message plus the status, so callers can
 *  show something useful without re-deriving it from an HttpErrorResponse. */
export class RagError extends Error {
  constructor(
    override readonly message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'RagError';
  }
}

@Injectable({ providedIn: 'root' })
export class Rag {
  private readonly http = inject(HttpClient);
  private readonly base = API_BASE;

  ask(question: string, conversationId?: number): Observable<RagAnswer> {
    return this.http
      .post<RagAnswer>(`${this.base}/ask/`, { question, conversation_id: conversationId })
      .pipe(catchError((err) => throwError(() => this.normalize(err))));
  }

  listConversations(): Observable<ConversationSummary[]> {
    return this.http
      .get<ConversationSummary[]>(`${this.base}/conversations/`)
      .pipe(catchError((err) => throwError(() => this.normalize(err))));
  }

  getConversation(id: number): Observable<ConversationDetail> {
    return this.http
      .get<ConversationDetail>(`${this.base}/conversations/${id}/`)
      .pipe(catchError((err) => throwError(() => this.normalize(err))));
  }

  deleteConversation(id: number): Observable<void> {
    return this.http
      .delete<void>(`${this.base}/conversations/${id}/`)
      .pipe(catchError((err) => throwError(() => this.normalize(err))));
  }

  private normalize(err: unknown): RagError {
    if (err instanceof HttpErrorResponse) {
      if (err.status === 0) {
        return new RagError('ارتباط با سرور برقرار نشد. اتصال شبکه را بررسی کنید.', 0);
      }
      const detail = (err.error && (err.error.error || err.error.detail)) as string | undefined;
      if (err.status >= 500) {
        return new RagError('خطای داخلی سرور. لطفاً بعداً دوباره تلاش کنید.', err.status);
      }
      return new RagError(detail || 'درخواست ناموفق بود.', err.status);
    }
    return new RagError('خطای ناشناخته رخ داد.', -1);
  }
}
