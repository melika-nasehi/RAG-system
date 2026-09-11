import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { tap } from 'rxjs/operators';
import { API_BASE } from '../shared/api-base';

export interface CorpusDocument {
  id: number;
  source: string;
  uploaded_at: string;
  uploaded_by: string | null;
  verdict: string;
  chunk_count: number;
  page_count: number | null;
}

export interface UploadResult {
  accepted: boolean;
  id?: number;
  source: string;
  reason: string;
  verdict?: string;
  chunks_added?: number;
  chunks_total?: number;
  digits_repaired?: boolean;
}

@Injectable({ providedIn: 'root' })
export class AdminApi {
  private readonly http = inject(HttpClient);
  private readonly url = `${API_BASE}/admin/documents/`;

  listDocuments(): Observable<CorpusDocument[]> {
    return this.http.get<CorpusDocument[]>(this.url);
  }

  uploadDocument(file: File): Observable<UploadResult> {
    const body = new FormData();
    body.append('file', file);
    return this.http.post<UploadResult>(this.url, body);
  }

  deleteDocument(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}${id}/`);
  }

  /** Fetches the PDF and hands the browser a save prompt — a plain `<a
   *  href>` can't carry the Authorization header this endpoint requires, so
   *  the file has to come through HttpClient first. */
  downloadDocument(id: number, filename: string): Observable<Blob> {
    return this.http
      .get(`${this.url}${id}/`, { responseType: 'blob' })
      .pipe(tap((blob) => saveBlob(blob, filename)));
  }
}

function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
