import { Injectable, computed, inject, signal } from '@angular/core';
import { Rag, RagError, type ConversationSummary } from '../services/rag';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources: string[];
}

export type Theme = 'light' | 'dark' | 'system';

const THEME_KEY = 'rag.theme';

let counter = 0;
const nextId = () => `m${Date.now()}_${counter++}`;

/** The single source of truth for the chat screen. Components read the
 *  signals and call the intent methods; none of them talk to the API or hold
 *  their own copy of the conversation. */
@Injectable({ providedIn: 'root' })
export class ChatStore {
  private readonly rag = inject(Rag);

  private readonly _messages = signal<ChatMessage[]>([]);
  private readonly _conversations = signal<ConversationSummary[]>([]);
  private readonly _activeId = signal<number | null>(null);
  private readonly _sending = signal(false);
  private readonly _loadingConversation = signal(false);
  private readonly _error = signal<string | null>(null);
  private readonly _drawerOpen = signal(false);
  private readonly _theme = signal<Theme>(this.readStoredTheme());

  // Bumped only by an explicit switch — openConversation() or
  // newConversation() — never by activeId acquiring an id as a side effect
  // of a new conversation's own first response landing. Consumers (the
  // message list, to reset its scroll-position tracking) need that
  // distinction: the latter must not override a scroll-up the user did
  // while that very response was in flight.
  private readonly _conversationSwitch = signal(0);

  private lastQuestion: string | null = null;

  readonly messages = this._messages.asReadonly();
  readonly conversations = this._conversations.asReadonly();
  readonly activeId = this._activeId.asReadonly();
  readonly sending = this._sending.asReadonly();
  readonly loadingConversation = this._loadingConversation.asReadonly();
  readonly error = this._error.asReadonly();
  readonly drawerOpen = this._drawerOpen.asReadonly();
  readonly theme = this._theme.asReadonly();
  readonly conversationSwitch = this._conversationSwitch.asReadonly();

  readonly isEmpty = computed(
    () => this._messages().length === 0 && !this._loadingConversation(),
  );
  readonly canRetry = computed(() => !!this._error() && !!this.lastQuestion && !this._sending());

  constructor() {
    this.applyTheme(this._theme());
    this.refreshConversations();
  }

  // ---- conversations list ----

  refreshConversations(): void {
    this.rag.listConversations().subscribe({
      next: (list) => this._conversations.set(list),
      error: () => {
        /* the list is non-critical; a failure here shouldn't block asking */
      },
    });
  }

  openConversation(id: number): void {
    if (id === this._activeId() && this._messages().length) {
      this.closeDrawer();
      return;
    }
    this._loadingConversation.set(true);
    this._error.set(null);
    this.closeDrawer();

    this.rag.getConversation(id).subscribe({
      next: (conv) => {
        this._messages.set(conv.messages.map((m) => ({ ...m, id: nextId() })));
        this._activeId.set(conv.id);
        this._loadingConversation.set(false);
        this._conversationSwitch.update((n) => n + 1);
      },
      error: (err: RagError) => {
        this._error.set(err.message);
        this._loadingConversation.set(false);
      },
    });
  }

  newConversation(): void {
    this._messages.set([]);
    this._activeId.set(null);
    this._error.set(null);
    this.lastQuestion = null;
    this.closeDrawer();
    this._conversationSwitch.update((n) => n + 1);
  }

  /** Removes a conversation for good — backend cascades to its messages and
   *  any feedback on them. If it was the open one, the view clears to the
   *  empty state exactly like starting a new conversation. */
  deleteConversation(id: number): void {
    this.rag.deleteConversation(id).subscribe({
      next: () => {
        this._conversations.update((list) => list.filter((c) => c.id !== id));
        if (this._activeId() === id) {
          this.newConversation();
        }
      },
      error: (err: RagError) => {
        this._error.set(err.message);
      },
    });
  }

  // ---- asking ----

  send(question: string): void {
    const q = question.trim();
    if (!q || this._sending()) return;

    this._messages.update((msgs) => [
      ...msgs,
      { id: nextId(), role: 'user', content: q, sources: [] },
    ]);
    this.dispatch(q);
  }

  /** Re-send the question whose answer failed. The user bubble is already on
   *  screen, so this only re-issues the request. */
  retry(): void {
    if (!this.lastQuestion || this._sending()) return;
    this.dispatch(this.lastQuestion);
  }

  private dispatch(q: string): void {
    this.lastQuestion = q;
    this._error.set(null);
    this._sending.set(true);

    this.rag.ask(q, this._activeId() ?? undefined).subscribe({
      next: (result) => {
        this._messages.update((msgs) => [
          ...msgs,
          {
            id: nextId(),
            role: 'assistant',
            content: result.answer,
            sources: result.sources,
          },
        ]);
        this._activeId.set(result.conversation_id);
        this._sending.set(false);
        this.lastQuestion = null;
        this.refreshConversations();
      },
      error: (err: RagError) => {
        this._sending.set(false);
        this._error.set(err.message);
      },
    });
  }

  dismissError(): void {
    this._error.set(null);
  }

  // ---- drawer (mobile) ----

  toggleDrawer(): void {
    this._drawerOpen.update((v) => !v);
  }

  closeDrawer(): void {
    this._drawerOpen.set(false);
  }

  // ---- theme ----

  cycleTheme(): void {
    const order: Theme[] = ['system', 'light', 'dark'];
    const next = order[(order.indexOf(this._theme()) + 1) % order.length];
    this._theme.set(next);
    this.applyTheme(next);
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      /* private mode / storage disabled — the choice just won't persist */
    }
  }

  private applyTheme(theme: Theme): void {
    const root = document.documentElement;
    if (theme === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
  }

  private readStoredTheme(): Theme {
    try {
      const stored = localStorage.getItem(THEME_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
    } catch {
      /* ignore */
    }
    return 'system';
  }
}
