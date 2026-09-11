import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { Rag, RagError } from './rag';

describe('Rag', () => {
  let service: Rag;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(Rag);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('is created', () => {
    expect(service).toBeTruthy();
  });

  it('posts a question to the ask endpoint', () => {
    let received: unknown;
    service.ask('سوال؟').subscribe((r) => (received = r));

    const req = httpMock.expectOne('http://localhost:8000/api/ask/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body.question).toBe('سوال؟');
    req.flush({ conversation_id: 1, question: 'سوال؟', answer: 'پاسخ', sources: [], backend: 'x' });

    expect(received).toBeTruthy();
  });

  it('maps a connection failure to a localised RagError', () => {
    let error: RagError | undefined;
    service.ask('x').subscribe({ error: (e) => (error = e) });

    httpMock.expectOne('http://localhost:8000/api/ask/').error(new ProgressEvent('error'), {
      status: 0,
    });

    expect(error).toBeInstanceOf(RagError);
    expect(error?.status).toBe(0);
    expect(error?.message).toContain('سرور');
  });
});
