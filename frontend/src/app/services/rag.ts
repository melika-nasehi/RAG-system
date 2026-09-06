import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface RagAnswer {
  question: string;
  answer: string;
  sources: string[];
  backend: string;
}

@Injectable({
  providedIn: 'root'
})
export class Rag {
  private readonly apiUrl = 'http://localhost:8000/api/ask/';

  constructor(private http: HttpClient) {}

  ask(question: string): Observable<RagAnswer> {
    return this.http.post<RagAnswer>(this.apiUrl, { question });
  }
}