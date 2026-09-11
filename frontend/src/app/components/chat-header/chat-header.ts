import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ChatStore } from '../../state/chat-store';

/** Slim top bar. Carries the drawer toggle on small screens and the product
 *  name; kept minimal so the transcript stays the focus. */
@Component({
  selector: 'app-chat-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="header">
      <button
        type="button"
        class="menu"
        aria-label="باز کردن منو"
        (click)="store.toggleDrawer()"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            d="M4 7h16M4 12h16M4 17h16"
          />
        </svg>
      </button>

      <div class="title">
        <h1>سامانه پرسش‌وپاسخ مقررات دانشگاهی</h1>
        <p>پاسخ مستند بر پایهٔ آیین‌نامه‌های رسمی</p>
      </div>

      <button
        type="button"
        class="new"
        aria-label="گفتگوی جدید"
        (click)="store.newConversation()"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            d="M12 5v14M5 12h14"
          />
        </svg>
      </button>
    </header>
  `,
  styles: `
    .header {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-5);
      background: var(--bg-elevated);
      border-bottom: 1px solid var(--border);
      min-height: 60px;
    }
    .menu,
    .new {
      width: 36px;
      height: 36px;
      border-radius: var(--radius-md);
      display: grid;
      place-items: center;
      color: var(--text-secondary);
      transition: background var(--transition-fast), color var(--transition-fast);
      flex-shrink: 0;
    }
    .menu:hover,
    .new:hover {
      background: var(--surface-hover);
      color: var(--text-primary);
    }
    .menu {
      display: none;
    }
    .title {
      flex: 1;
      min-width: 0;
    }
    .title h1 {
      font-size: var(--text-md);
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .title p {
      font-size: var(--text-xs);
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .new {
      display: none;
    }

    @media (max-width: 1024px) {
      .menu {
        display: grid;
      }
      .new {
        display: grid;
      }
    }
    @media (max-width: 720px) {
      .header {
        padding: var(--space-2) var(--space-3);
      }
      .title p {
        display: none;
      }
    }
  `,
})
export class ChatHeader {
  protected readonly store = inject(ChatStore);
}
