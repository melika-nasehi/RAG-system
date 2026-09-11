import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ChatStore } from './chat-store';

const ASK = 'http://localhost:8000/api/ask/';
const LIST = 'http://localhost:8000/api/conversations/';
const detail = (id: number) => `http://localhost:8000/api/conversations/${id}/`;

describe('ChatStore', () => {
  let store: ChatStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), ChatStore],
    });
    store = TestBed.inject(ChatStore);
    http = TestBed.inject(HttpTestingController);
    // The constructor kicks off a conversation-list load.
    http.expectOne(LIST).flush([]);
  });

  afterEach(() => http.verify());

  it('starts empty', () => {
    expect(store.messages()).toEqual([]);
    expect(store.isEmpty()).toBe(true);
  });

  it('adds the user turn immediately and the answer on success', () => {
    store.send('حداکثر واحد؟');

    expect(store.messages().length).toBe(1);
    expect(store.messages()[0]).toMatchObject({ role: 'user', content: 'حداکثر واحد؟' });
    expect(store.sending()).toBe(true);

    http.expectOne(ASK).flush({
      conversation_id: 7,
      question: 'حداکثر واحد؟',
      answer: 'حداکثر ۲۰ واحد.',
      sources: ['آیین‌نامه آموزشی.pdf، صفحه ۳'],
      backend: 'gemini',
    });

    expect(store.sending()).toBe(false);
    expect(store.messages().length).toBe(2);
    expect(store.messages()[1]).toMatchObject({ role: 'assistant', content: 'حداکثر ۲۰ واحد.' });
    expect(store.activeId()).toBe(7);
    http.expectOne(LIST).flush([]); // refresh after answer
  });

  it('surfaces a localised error and allows retry without a duplicate user turn', () => {
    store.send('سوال؟');
    http.expectOne(ASK).error(new ProgressEvent('error'), { status: 0 });

    expect(store.sending()).toBe(false);
    expect(store.error()).toContain('سرور');
    expect(store.canRetry()).toBe(true);
    expect(store.messages().length).toBe(1);

    store.retry();
    expect(store.messages().length).toBe(1); // still just the one user turn
    http.expectOne(ASK).flush({
      conversation_id: 1,
      question: 'سوال؟',
      answer: 'پاسخ.',
      sources: [],
      backend: 'gemini',
    });

    expect(store.error()).toBeNull();
    expect(store.messages().length).toBe(2);
    http.expectOne(LIST).flush([]);
  });

  it('deleteConversation removes it from the list', () => {
    store.refreshConversations();
    http.expectOne(LIST).flush([
      { id: 5, title: 'a', updated_at: 't' },
      { id: 6, title: 'b', updated_at: 't' },
    ]);
    expect(store.conversations().length).toBe(2);

    store.deleteConversation(5);
    http.expectOne(detail(5)).flush(null, { status: 204, statusText: 'No Content' });

    expect(store.conversations().map((c) => c.id)).toEqual([6]);
  });

  it('deleting the open conversation clears the view to empty', () => {
    store.send('x');
    http.expectOne(ASK).flush({ conversation_id: 9, question: 'x', answer: 'y', sources: [], backend: 'g' });
    http.expectOne(LIST).flush([{ id: 9, title: 'x', updated_at: 't' }]);
    expect(store.activeId()).toBe(9);

    store.deleteConversation(9);
    http.expectOne(detail(9)).flush(null, { status: 204, statusText: 'No Content' });

    expect(store.activeId()).toBeNull();
    expect(store.messages()).toEqual([]);
  });

  it('deleting a conversation that is not the open one leaves the view alone', () => {
    store.send('x');
    http.expectOne(ASK).flush({ conversation_id: 9, question: 'x', answer: 'y', sources: [], backend: 'g' });
    http.expectOne(LIST).flush([{ id: 9, title: 'x', updated_at: 't' }]);

    store.deleteConversation(123); // some other conversation, not the open one
    http.expectOne(detail(123)).flush(null, { status: 204, statusText: 'No Content' });

    expect(store.activeId()).toBe(9);
    expect(store.messages().length).toBe(2);
  });

  it('surfaces an error and keeps the conversation on delete failure', () => {
    store.refreshConversations();
    http.expectOne(LIST).flush([{ id: 5, title: 'a', updated_at: 't' }]);

    store.deleteConversation(5);
    http.expectOne(detail(5)).error(new ProgressEvent('error'), { status: 0 });

    expect(store.error()).toContain('سرور');
    expect(store.conversations().map((c) => c.id)).toEqual([5]);
  });

  it('newConversation clears the transcript and active id', () => {
    store.send('x');
    http.expectOne(ASK).flush({
      conversation_id: 3,
      question: 'x',
      answer: 'y',
      sources: [],
      backend: 'g',
    });
    http.expectOne(LIST).flush([]);

    store.newConversation();
    expect(store.messages()).toEqual([]);
    expect(store.activeId()).toBeNull();
  });
});
