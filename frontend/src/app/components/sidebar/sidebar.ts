import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ChatStore } from '../../state/chat-store';
import { AuthStore } from '../../state/auth-store';
import { timeAgo } from '../../shared/persian';

/** Conversation history and the "new chat" action. On narrow screens this is
 *  rendered inside a drawer by the shell; the markup is the same either way. */
@Component({
  selector: 'app-sidebar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="sidebar">
      <div class="brand">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18">
            <path
              fill="currentColor"
              d="M12 3 3 7v2l9 4 7-3.1V15h2V7l-9-4Zm-6 9.2V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-3.8l-6 2.6-6-2.6Z"
            />
          </svg>
        </span>
        <span class="name">مقررات دانشجویی</span>
        <button type="button" class="close" aria-label="بستن منو" (click)="store.closeDrawer()">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path
              fill="none"
              stroke="currentColor"
              stroke-width="2.2"
              stroke-linecap="round"
              d="m6 6 12 12M18 6 6 18"
            />
          </svg>
        </button>
      </div>

      <button type="button" class="new-chat" (click)="store.newConversation()">
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
          <path
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            d="M12 5v14M5 12h14"
          />
        </svg>
        گفتگوی جدید
      </button>

      <nav class="history" aria-label="تاریخچهٔ گفتگوها">
        @if (store.conversations().length === 0) {
          <p class="empty">هنوز گفتگویی ثبت نشده است.</p>
        } @else {
          @for (conversation of store.conversations(); track conversation.id) {
            <div class="entry" [class.active]="conversation.id === store.activeId()">
              <button
                type="button"
                class="entry-open"
                (click)="store.openConversation(conversation.id)"
              >
                <span class="title">{{ conversation.title || 'بدون عنوان' }}</span>
                <span class="time">{{ ago(conversation.updated_at) }}</span>
              </button>

              @if (confirmingDeleteId() === conversation.id) {
                <div class="confirm-delete" animate.enter="pop">
                  <button
                    type="button"
                    class="confirm-yes"
                    aria-label="تأیید حذف گفتگو"
                    (click)="confirmDelete($event, conversation.id)"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                      <path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" d="m5 12 5 5 9-10" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="confirm-no"
                    aria-label="انصراف از حذف"
                    (click)="cancelDelete($event)"
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                      <path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" d="m6 6 12 12M18 6 6 18" />
                    </svg>
                  </button>
                </div>
              } @else {
                <button
                  type="button"
                  class="delete"
                  aria-label="حذف گفتگوی «{{ conversation.title || 'بدون عنوان' }}»"
                  (click)="askDelete($event, conversation.id)"
                >
                  <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
                    <path
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0-.7 12.1a2 2 0 0 1-2 1.9H9.7a2 2 0 0 1-2-1.9L7 7h10Z"
                    />
                  </svg>
                </button>
              }
            </div>
          }
        }
      </nav>

      @if (auth.user(); as user) {
        <div class="account">
          <div class="who">
            <span class="avatar" aria-hidden="true">{{ initial(user.username) }}</span>
            <span class="username">{{ user.username }}</span>
            @if (user.is_admin) {
              <span class="badge">مدیر</span>
            }
          </div>
          @if (user.is_admin) {
            <a routerLink="/admin/documents" class="admin-link" (click)="store.closeDrawer()">
              <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
                <path fill="currentColor" d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm7 1.5V7h3.5L13 3.5Z" />
              </svg>
              مدیریت اسناد
            </a>
          }
          <button type="button" class="logout" (click)="auth.logout()">
            <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
              <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M15 12H6m3-3-3 3 3 3m4-9h4a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1h-4" />
            </svg>
            خروج از حساب
          </button>
        </div>
      }

      <div class="footer">
        <span class="org">دانشگاه زنجان</span>
        <button type="button" class="theme" (click)="store.cycleTheme()">
          @switch (store.theme()) {
            @case ('light') {
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Zm0-5a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm0 16a1 1 0 0 1 1 1v2a1 1 0 1 1-2 0v-2a1 1 0 0 1 1-1ZM4.2 4.2a1 1 0 0 1 1.4 0l1.5 1.5A1 1 0 0 1 5.7 7.1L4.2 5.6a1 1 0 0 1 0-1.4Zm12.7 12.7a1 1 0 0 1 1.4 0l1.5 1.5a1 1 0 0 1-1.4 1.4l-1.5-1.5a1 1 0 0 1 0-1.4ZM2 12a1 1 0 0 1 1-1h2a1 1 0 1 1 0 2H3a1 1 0 0 1-1-1Zm17 0a1 1 0 0 1 1-1h2a1 1 0 1 1 0 2h-2a1 1 0 0 1-1-1ZM4.2 19.8a1 1 0 0 1 0-1.4l1.5-1.5a1 1 0 0 1 1.4 1.4l-1.5 1.5a1 1 0 0 1-1.4 0ZM16.9 7.1a1 1 0 0 1 0-1.4l1.5-1.5a1 1 0 1 1 1.4 1.4l-1.5 1.5a1 1 0 0 1-1.4 0Z"
                />
              </svg>
              روشن
            }
            @case ('dark') {
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M12.3 3a1 1 0 0 0-.4 1.9 6 6 0 1 1-7 8.8A1 1 0 0 0 3 14a9 9 0 1 0 9.3-11Z"
                />
              </svg>
              تیره
            }
            @default {
              <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-5v2h3a1 1 0 1 1 0 2H8a1 1 0 1 1 0-2h3v-2H6a2 2 0 0 1-2-2V5Z"
                />
              </svg>
              خودکار
            }
          }
        </button>
      </div>
    </div>
  `,
  styles: `
    .sidebar {
      width: var(--sidebar-width);
      height: 100%;
      display: flex;
      flex-direction: column;
      background: var(--sidebar-bg);
      border-inline-end: 1px solid var(--sidebar-border);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-4) var(--space-4) var(--space-3);
    }
    .logo {
      width: 30px;
      height: 30px;
      border-radius: var(--radius-md);
      display: grid;
      place-items: center;
      background: var(--accent-soft);
      color: var(--accent);
      flex-shrink: 0;
    }
    .name {
      font-weight: 700;
      font-size: var(--text-sm);
      flex: 1;
    }
    .close {
      display: none;
      width: 30px;
      height: 30px;
      border-radius: var(--radius-sm);
      color: var(--text-muted);
    }
    .close:hover {
      background: var(--surface-hover);
      color: var(--text-primary);
    }

    .new-chat {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--space-2);
      margin: 0 var(--space-3) var(--space-3);
      padding: var(--space-3);
      border-radius: var(--radius-md);
      background: var(--accent);
      color: var(--text-on-accent);
      font-size: var(--text-sm);
      font-weight: 600;
      transition: background var(--transition-fast);
    }
    .new-chat:hover {
      background: var(--accent-hover);
    }

    .history {
      flex: 1;
      overflow-y: auto;
      padding: 0 var(--space-2) var(--space-3);
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .empty {
      color: var(--text-muted);
      font-size: var(--text-xs);
      padding: var(--space-3);
      text-align: center;
    }
    .entry {
      display: flex;
      align-items: center;
      gap: var(--space-1);
      border-radius: var(--radius-sm);
      transition: background var(--transition-fast);
    }
    .entry:hover {
      background: var(--surface-hover);
    }
    .entry.active {
      background: var(--accent-soft);
    }
    .entry.active .title {
      color: var(--accent-soft-text);
      font-weight: 600;
    }
    .entry-open {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
      text-align: start;
      padding: var(--space-2) var(--space-3);
    }
    .title {
      font-size: var(--text-sm);
      color: var(--text-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 100%;
    }
    .time {
      font-size: 0.68rem;
      color: var(--text-muted);
    }

    .delete {
      flex-shrink: 0;
      width: 26px;
      height: 26px;
      margin-inline-end: var(--space-2);
      border-radius: var(--radius-sm);
      display: grid;
      place-items: center;
      color: var(--text-muted);
      opacity: 0;
      transition: opacity var(--transition-fast), background var(--transition-fast),
        color var(--transition-fast);
    }
    .entry:hover .delete,
    .entry:focus-within .delete {
      opacity: 1;
    }
    .delete:hover {
      background: var(--danger-soft);
      color: var(--danger);
    }
    /* A touch device has no hover to reveal the button on — keep it visible. */
    @media (hover: none) {
      .delete {
        opacity: 1;
      }
    }

    .confirm-delete {
      flex-shrink: 0;
      display: flex;
      gap: 2px;
      margin-inline-end: var(--space-2);
    }
    .confirm-yes,
    .confirm-no {
      width: 26px;
      height: 26px;
      border-radius: var(--radius-sm);
      display: grid;
      place-items: center;
    }
    .confirm-yes {
      background: var(--danger);
      color: white;
    }
    .confirm-yes:hover {
      opacity: 0.85;
    }
    .confirm-no {
      color: var(--text-secondary);
    }
    .confirm-no:hover {
      background: var(--surface-hover);
      color: var(--text-primary);
    }
    .pop {
      animation: pop var(--transition-fast) both;
    }
    @keyframes pop {
      from {
        opacity: 0;
        transform: scale(0.8);
      }
    }

    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--space-3) var(--space-4);
      border-top: 1px solid var(--sidebar-border);
    }
    .org {
      font-size: var(--text-xs);
      color: var(--text-muted);
    }
    .theme {
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-1) var(--space-2);
      border-radius: var(--radius-sm);
      font-size: var(--text-xs);
      color: var(--text-secondary);
      transition: background var(--transition-fast), color var(--transition-fast);
    }
    .theme:hover {
      background: var(--surface-hover);
      color: var(--text-primary);
    }

    .account {
      border-top: 1px solid var(--sidebar-border);
      padding: var(--space-3);
      display: flex;
      flex-direction: column;
      gap: var(--space-1);
    }
    .who {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-1) var(--space-2) var(--space-2);
    }
    .avatar {
      width: 26px;
      height: 26px;
      border-radius: var(--radius-full);
      display: grid;
      place-items: center;
      background: var(--accent);
      color: var(--text-on-accent);
      font-size: var(--text-xs);
      font-weight: 700;
      flex-shrink: 0;
    }
    .username {
      flex: 1;
      font-size: var(--text-sm);
      font-weight: 600;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .badge {
      font-size: 0.62rem;
      font-weight: 700;
      color: var(--accent-soft-text);
      background: var(--accent-soft);
      border-radius: var(--radius-full);
      padding: 1px 6px;
    }
    .admin-link,
    .logout {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2);
      border-radius: var(--radius-sm);
      font-size: var(--text-xs);
      color: var(--text-secondary);
      transition: background var(--transition-fast), color var(--transition-fast);
    }
    
    .admin-link:hover,
    .logout:hover {
      background: var(--surface-hover);
      color: var(--text-primary);
    }

    @media (max-width: 1024px) {
      .close {
        display: grid;
      }
      .sidebar {
        box-shadow: var(--shadow-lg);
      }
    }
  `,
})
export class Sidebar {
  protected readonly store = inject(ChatStore);
  protected readonly auth = inject(AuthStore);
  protected readonly ago = timeAgo;

  // Which conversation (if any) is showing its "really delete this?" step,
  // instead of a browser confirm() — keeps a stray click from deleting
  // history outright while staying out of the way otherwise.
  protected readonly confirmingDeleteId = signal<number | null>(null);

  protected initial(username: string): string {
    return username.charAt(0).toUpperCase();
  }

  protected askDelete(event: Event, id: number): void {
    event.stopPropagation();
    this.confirmingDeleteId.set(id);
  }

  protected confirmDelete(event: Event, id: number): void {
    event.stopPropagation();
    this.store.deleteConversation(id);
    this.confirmingDeleteId.set(null);
  }

  protected cancelDelete(event: Event): void {
    event.stopPropagation();
    this.confirmingDeleteId.set(null);
  }
}
