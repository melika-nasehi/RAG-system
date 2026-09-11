import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  afterRenderEffect,
  computed,
  effect,
  inject,
  output,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { ChatStore } from '../../state/chat-store';
import { Message } from '../message/message';
import { Welcome } from '../welcome/welcome';
import { TypingDots } from '../typing-dots/typing-dots';
import { ErrorBanner } from '../error-banner/error-banner';

/** The scrolling transcript: welcome screen, message turns, the thinking
 *  indicator, and any error — kept pinned to the bottom as content arrives. */
@Component({
  selector: 'app-message-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Message, Welcome, TypingDots, ErrorBanner],
  template: `
    <div #scroll class="scroll" (scroll)="onScroll()">
      <div class="inner">
        @if (store.isEmpty()) {
          <app-welcome (pick)="pick.emit($event)" />
        } @else {
          @if (store.loadingConversation()) {
            <div class="loading">
              @for (row of skeleton; track $index) {
                <div class="skeleton-row">
                  <div class="skeleton-avatar"></div>
                  <div class="skeleton-lines">
                    <span></span><span></span><span></span>
                  </div>
                </div>
              }
            </div>
          } @else {
            <div class="stream" aria-live="polite">
              @for (message of store.messages(); track message.id) {
                <app-message [message]="message" animate.enter="turn-in" />
              }

              @if (store.sending()) {
                <div class="thinking" animate.enter="turn-in">
                  <div class="avatar" aria-hidden="true"><span>آ</span></div>
                  <div class="bubble"><app-typing-dots /></div>
                </div>
              }
            </div>
          }
        }

        @if (store.error()) {
          <app-error-banner
            class="error-slot"
            [message]="store.error()!"
            [canRetry]="store.canRetry()"
            (retry)="store.retry()"
            (dismiss)="store.dismissError()"
          />
        }
      </div>
    </div>
  `,
  styles: `
    /* MessageList's host element — <app-message-list> — is .scroll's real
       DOM parent. Without this, it's an unstyled block box: .scroll's
       "flex: 1" below has no flex container to size against, so .scroll
       just grows to fit all its content instead of being capped to the
       space .main has for it, and overflow-y: auto never gets anything to
       act on. The host has to join the flex column itself, and needs its
       own min-height: 0 — a flex item's default automatic minimum size is
       "big enough for my content", which recreates exactly this bug one
       level up otherwise (the classic flex-child-won't-shrink trap). */
    :host {
      display: flex;
      flex-direction: column;
      flex: 1 1 0%;
      min-height: 0;
    }
    .scroll {
      flex: 1;
      overflow-y: auto;
      overscroll-behavior: contain;
    }
    .inner {
      max-width: 60rem;
      margin: 0 auto;
      padding: var(--space-5) var(--space-5) var(--space-6);
      min-height: 100%;
      display: flex;
      flex-direction: column;
    }
    .stream {
      display: flex;
      flex-direction: column;
      gap: var(--space-5);
    }
    .thinking {
      display: flex;
      gap: var(--space-3);
    }
    .thinking .avatar {
      flex-shrink: 0;
      width: 30px;
      height: 30px;
      border-radius: var(--radius-full);
      display: grid;
      place-items: center;
      background: var(--accent);
      color: var(--text-on-accent);
      font-size: 0.9rem;
      font-weight: 700;
    }
    .thinking .bubble {
      padding: var(--space-3) var(--space-4);
      background: var(--assistant-bubble-bg);
      border: 1px solid var(--assistant-bubble-border);
      border-radius: var(--radius-lg);
      border-end-start-radius: var(--radius-sm);
    }
    .error-slot {
      margin-top: var(--space-5);
    }

    .loading {
      display: flex;
      flex-direction: column;
      gap: var(--space-5);
    }
    .skeleton-row {
      display: flex;
      gap: var(--space-3);
    }
    .skeleton-row:nth-child(even) {
      flex-direction: row-reverse;
    }
    .skeleton-avatar {
      width: 30px;
      height: 30px;
      border-radius: var(--radius-full);
      background: var(--surface-sunken);
      flex-shrink: 0;
    }
    .skeleton-lines {
      flex: 1;
      max-width: 32rem;
      display: flex;
      flex-direction: column;
      gap: var(--space-2);
    }
    .skeleton-lines span {
      height: 12px;
      border-radius: var(--radius-sm);
      background: linear-gradient(
        90deg,
        var(--surface-sunken) 0%,
        var(--surface-hover) 50%,
        var(--surface-sunken) 100%
      );
      background-size: 200% 100%;
      animation: shimmer 1.4s ease-in-out infinite;
    }
    .skeleton-lines span:nth-child(2) {
      width: 90%;
    }
    .skeleton-lines span:nth-child(3) {
      width: 60%;
    }
    @keyframes shimmer {
      to {
        background-position: -200% 0;
      }
    }

    .turn-in {
      animation: turn-in var(--transition-slow) both;
    }
    @keyframes turn-in {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
    }

    @media (max-width: 720px) {
      .inner {
        padding: var(--space-4) var(--space-3) var(--space-5);
      }
      .stream {
        gap: var(--space-4);
      }
    }
  `,
})
export class MessageList {
  protected readonly store = inject(ChatStore);
  readonly pick = output<string>();

  protected readonly skeleton = [0, 1, 2];

  private readonly scroll = viewChild.required<ElementRef<HTMLDivElement>>('scroll');

  /** A single value that changes exactly when something new should bring the
   *  view to the bottom — a turn added, or the thinking indicator toggled. */
  private readonly bottomTrigger = computed(
    () => `${this.store.messages().length}:${this.store.sending()}`,
  );

  // Within this many pixels of the bottom counts as "at the bottom" — close
  // enough that snapping the rest of the way isn't a jarring jump.
  private static readonly NEAR_BOTTOM_PX = 96;

  /** Whether a new turn should pull the view down. Kept in sync by onScroll
   *  as the user scrolls, so by the time a new message arrives it already
   *  reflects where they were a moment ago — not a position recomputed
   *  after the new content already changed scrollHeight. */
  private readonly stickToBottom = signal(true);

  constructor() {
    // A conversation switch is a wholesale content swap, not "new content
    // arrived while reading" — always start pinned to the bottom of it.
    // conversationSwitch (not activeId) is the signal for this: activeId
    // also changes the moment a brand-new conversation's own first response
    // assigns it an id, which must NOT reset the pin — that's exactly the
    // in-flight-response case this whole mechanism exists to respect.
    effect(() => {
      this.store.conversationSwitch();
      this.stickToBottom.set(true);
    });

    afterRenderEffect(() => {
      this.bottomTrigger();

      // A turn the user just sent themselves always shows — they took the
      // action, they see the result, regardless of where they'd scrolled.
      // An incoming assistant turn only pulls the view down if they were
      // already near the bottom (checked via the position onScroll last
      // recorded, from before this content arrived).
      const messages = untracked(this.store.messages);
      if (messages[messages.length - 1]?.role === 'user') {
        this.stickToBottom.set(true);
      }

      if (!untracked(this.stickToBottom)) return;
      const el = this.scroll().nativeElement;
      el.scrollTop = el.scrollHeight;
    });
  }

  protected onScroll(): void {
    const el = this.scroll().nativeElement;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    this.stickToBottom.set(distanceFromBottom <= MessageList.NEAR_BOTTOM_PX);
  }
}
