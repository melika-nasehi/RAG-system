import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import type { ChatMessage } from '../../state/chat-store';
import { renderMarkdown } from '../../shared/markdown';
import { Sources } from '../sources/sources';

/** One turn in the conversation. The user's text is shown verbatim; the
 *  assistant's is run through the small Markdown renderer and can be copied
 *  and expanded to its sources. */
@Component({
  selector: 'app-message',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Sources],
  template: `
    <article class="row" [class.user]="isUser()" [class.assistant]="!isUser()">
      <div class="avatar" aria-hidden="true">
        @if (isUser()) {
          <svg viewBox="0 0 24 24" width="17" height="17">
            <path
              fill="currentColor"
              d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-5 0-9 2.7-9 6v1a1 1 0 0 0 1 1h16a1 1 0 0 0 1-1v-1c0-3.3-4-6-9-6Z"
            />
          </svg>
        } @else {
          <span class="glyph">آ</span>
        }
      </div>

      <div class="body">
        <div class="bubble">
          @if (isUser()) {
            <p class="plain">{{ message().content }}</p>
          } @else {
            <div class="prose" [innerHTML]="html()"></div>
            <app-sources [sources]="message().sources" />
          }
        </div>

        @if (!isUser()) {
          <div class="tools">
            <button type="button" class="tool" (click)="copy()">
              @if (copied()) {
                <span>کپی شد</span>
              } @else {
                <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M9 3h9a2 2 0 0 1 2 2v11h-2V5H9V3Zm-4 4h9a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z"
                  />
                </svg>
                <span>کپی</span>
              }
            </button>
          </div>
        }
      </div>
    </article>
  `,
  styles: `
    .row {
      display: flex;
      gap: var(--space-3);
      max-width: 100%;
    }
    .row.user {
      flex-direction: row-reverse;
    }
    .avatar {
      flex-shrink: 0;
      width: 30px;
      height: 30px;
      border-radius: var(--radius-full);
      display: grid;
      place-items: center;
      margin-top: 2px;
    }
    .row.assistant .avatar {
      background: var(--accent);
      color: var(--text-on-accent);
    }
    .row.user .avatar {
      background: var(--surface-sunken);
      color: var(--text-muted);
      border: 1px solid var(--border);
    }
    .glyph {
      font-size: 0.9rem;
      font-weight: 700;
    }
    .body {
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: var(--space-1);
    }
    .row.user .body {
      align-items: flex-end;
    }
    .bubble {
      padding: var(--space-3) var(--space-4);
      border-radius: var(--radius-lg);
      font-size: var(--text-base);
      line-height: var(--leading-relaxed);
      overflow-wrap: anywhere;
    }
    .row.user .bubble {
      background: var(--user-bubble-bg);
      color: var(--user-bubble-text);
      border-end-end-radius: var(--radius-sm);
      max-width: min(46ch, 100%);
    }
    .row.assistant .bubble {
      background: var(--assistant-bubble-bg);
      color: var(--text-primary);
      border: 1px solid var(--assistant-bubble-border);
      border-end-start-radius: var(--radius-sm);
      box-shadow: var(--shadow-xs);
      max-width: var(--content-measure);
    }
    .plain {
      white-space: pre-wrap;
    }

    .prose :first-child {
      margin-top: 0;
    }
    .prose :last-child {
      margin-bottom: 0;
    }
    .prose p {
      margin: 0 0 var(--space-3);
    }
    .prose ul,
    .prose ol {
      margin: 0 0 var(--space-3);
      padding-inline-start: 1.4em;
    }
    .prose li {
      margin-bottom: var(--space-1);
    }
    .prose h1,
    .prose h2,
    .prose h3,
    .prose h4 {
      font-size: var(--text-md);
      margin: var(--space-4) 0 var(--space-2);
      font-weight: 700;
    }
    .prose strong {
      font-weight: 700;
    }
    .prose code {
      font-family: var(--font-mono);
      font-size: 0.9em;
      background: var(--surface-sunken);
      padding: 1px 5px;
      border-radius: var(--radius-sm);
    }

    .tools {
      display: flex;
      gap: var(--space-1);
      opacity: 0;
      transition: opacity var(--transition-fast);
    }
    .row:hover .tools,
    .tools:focus-within {
      opacity: 1;
    }
    .tool {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: var(--text-xs);
      color: var(--text-muted);
      padding: var(--space-1) var(--space-2);
      border-radius: var(--radius-sm);
      transition: color var(--transition-fast), background var(--transition-fast);
    }
    .tool:hover {
      color: var(--text-primary);
      background: var(--surface-hover);
    }

    @media (hover: none) {
      .tools {
        opacity: 1;
      }
    }
  `,
})
export class Message {
  readonly message = input.required<ChatMessage>();
  readonly copied = signal(false);

  readonly isUser = computed(() => this.message().role === 'user');
  readonly html = computed(() => renderMarkdown(this.message().content));

  async copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.message().content);
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 1600);
    } catch {
      /* clipboard blocked — nothing useful to show the user here */
    }
  }
}
