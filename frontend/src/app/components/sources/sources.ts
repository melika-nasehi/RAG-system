import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { parseSource, toPersianDigits } from '../../shared/persian';

/** The citations behind an answer, collapsed by default. Each row shows the
 *  document name with its page as a separate pill, matching how the
 *  regulations are referenced. */
@Component({
  selector: 'app-sources',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (items().length) {
      <div class="sources" [class.open]="open()">
        <button
          type="button"
          class="toggle"
          [attr.aria-expanded]="open()"
          (click)="open.set(!open())"
        >
          <svg class="chevron" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">
            <path fill="none" stroke="currentColor" stroke-width="2.5" d="m6 9 6 6 6-6" />
          </svg>
          <span>منابع</span>
          <span class="count">{{ count() }}</span>
        </button>

        @if (open()) {
          <ul class="list" animate.enter="reveal">
            @for (item of items(); track item.raw) {
              <li class="item">
                <svg class="doc" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                  <path
                    fill="currentColor"
                    d="M6 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm7 1.5V7h3.5L13 3.5Z"
                  />
                </svg>
                <span class="name">{{ item.document }}</span>
                @if (item.page) {
                  <span class="page">صفحه {{ item.page }}</span>
                }
              </li>
            }
          </ul>
        }
      </div>
    }
  `,
  styles: `
    .sources {
      margin-top: var(--space-3);
      border-top: 1px solid var(--border);
      padding-top: var(--space-2);
    }
    .toggle {
      display: inline-flex;
      align-items: center;
      gap: var(--space-2);
      font-size: var(--text-xs);
      color: var(--text-secondary);
      padding: var(--space-1) var(--space-2);
      border-radius: var(--radius-sm);
      transition: color var(--transition-fast), background var(--transition-fast);
    }
    .toggle:hover {
      color: var(--text-primary);
      background: var(--surface-hover);
    }
    .chevron {
      transition: transform var(--transition);
    }
    .sources.open .chevron {
      transform: rotate(180deg);
    }
    .count {
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--accent-soft);
      color: var(--accent-soft-text);
      border-radius: var(--radius-full);
      font-size: 0.68rem;
      font-weight: 700;
    }
    .list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: var(--space-1);
      margin-top: var(--space-2);
    }
    .item {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      padding: var(--space-2) var(--space-3);
      background: var(--surface-sunken);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      font-size: var(--text-xs);
    }
    .doc {
      color: var(--text-muted);
      flex-shrink: 0;
    }
    .name {
      flex: 1;
      color: var(--text-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .page {
      flex-shrink: 0;
      padding: 2px 8px;
      background: var(--accent-soft);
      color: var(--accent-soft-text);
      border-radius: var(--radius-full);
      font-weight: 600;
      font-size: 0.7rem;
    }
    .reveal {
      animation: reveal var(--transition-slow) both;
    }
    @keyframes reveal {
      from {
        opacity: 0;
        transform: translateY(-4px);
      }
    }
  `,
})
export class Sources {
  readonly sources = input.required<string[]>();
  readonly open = signal(false);

  readonly items = computed(() =>
    this.sources().map((raw) => ({ raw, ...parseSource(raw) })),
  );
  readonly count = computed(() => toPersianDigits(this.items().length));
}
