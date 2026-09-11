import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { MessageList } from './message-list';
import { ChatStore } from '../../state/chat-store';

const LIST = 'http://localhost:8000/api/conversations/';
const ASK = 'http://localhost:8000/api/ask/';

/** jsdom never computes real layout, so scrollHeight/clientHeight/scrollTop
 *  read as 0 by default. Stub them to the geometry a scenario needs, so the
 *  component's stick-to-bottom *logic* — the actual point of these tests,
 *  not pixel-perfect layout, which is covered separately in a real browser
 *  (see docs/) — can be exercised deterministically. */
function stubScrollGeometry(
  el: HTMLElement,
  { scrollHeight, clientHeight, scrollTop }: { scrollHeight: number; clientHeight: number; scrollTop: number },
) {
  Object.defineProperty(el, 'scrollHeight', { value: scrollHeight, configurable: true });
  Object.defineProperty(el, 'clientHeight', { value: clientHeight, configurable: true });
  let top = scrollTop;
  Object.defineProperty(el, 'scrollTop', {
    get: () => top,
    set: (v: number) => {
      top = v;
    },
    configurable: true,
  });
}

describe('MessageList — stick-to-bottom scrolling', () => {
  let http: HttpTestingController;
  let store: ChatStore;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    http = TestBed.inject(HttpTestingController);
    store = TestBed.inject(ChatStore);
    http.expectOne(LIST).flush([]); // the store's own constructor load
  });

  afterEach(() => http.verify());

  async function create() {
    const fixture = TestBed.createComponent(MessageList);
    fixture.detectChanges();
    await fixture.whenStable();
    const scrollEl = fixture.nativeElement.querySelector('.scroll') as HTMLElement;
    return { fixture, scrollEl };
  }

  function flushAsk(answer = 'پاسخ', conversationId = 1) {
    http
      .expectOne(ASK)
      .flush({ conversation_id: conversationId, question: 'x', answer, sources: [], backend: 'test' });
    // A successful ask() refreshes the sidebar's conversation list too.
    http.expectOne(LIST).flush([]);
  }

  it('auto-scrolls to the new bottom when the user was already near it', async () => {
    const { fixture, scrollEl } = await create();
    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 950 }); // 50px from bottom
    scrollEl.dispatchEvent(new Event('scroll'));

    store.send('سوال');
    fixture.detectChanges();
    await fixture.whenStable();
    flushAsk();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(scrollEl.scrollTop).toBe(1000);
  });

  it('does not force-scroll when the user has scrolled up to read earlier content', async () => {
    const { fixture, scrollEl } = await create();

    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 950 });
    scrollEl.dispatchEvent(new Event('scroll'));
    store.send('سوال');
    fixture.detectChanges();
    await fixture.whenStable();

    // While the answer is in flight, they scroll far up to read history.
    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 50 });
    scrollEl.dispatchEvent(new Event('scroll'));

    flushAsk();
    fixture.detectChanges();
    await fixture.whenStable();

    expect(scrollEl.scrollTop).toBe(50); // left exactly where they were
  });

  it('always shows a message the user just sent, even from a scrolled-up position', async () => {
    const { fixture, scrollEl } = await create();
    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 50 });
    scrollEl.dispatchEvent(new Event('scroll'));

    store.send('سوال جدید');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(scrollEl.scrollTop).toBe(1000);
    flushAsk();
  });

  it('resets to sticking on a conversation switch', async () => {
    const { fixture, scrollEl } = await create();
    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 50 });
    scrollEl.dispatchEvent(new Event('scroll'));
    store.send('سوال');
    fixture.detectChanges();
    await fixture.whenStable();
    flushAsk();
    fixture.detectChanges();
    await fixture.whenStable();

    store.newConversation();
    stubScrollGeometry(scrollEl, { scrollHeight: 1000, clientHeight: 600, scrollTop: 50 });
    store.send('سوال دیگر');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(scrollEl.scrollTop).toBe(1000);
    flushAsk('پاسخ', 2);
  });
});
