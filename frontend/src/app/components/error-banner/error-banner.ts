import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/** Inline, dismissible error with an optional retry action. Rendered in the
 *  message stream so the failure sits where the answer would have been. */
@Component({
  selector: 'app-error-banner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="banner" role="alert" animate.enter="pop">
      <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
        <path
          fill="currentColor"
          d="M12 2 1 21h22L12 2Zm0 6a1 1 0 0 1 1 1v5a1 1 0 1 1-2 0V9a1 1 0 0 1 1-1Zm0 10.5a1.25 1.25 0 1 1 0-2.5 1.25 1.25 0 0 1 0 2.5Z"
        />
      </svg>
      <span class="text">{{ message() }}</span>
      <div class="actions">
        @if (canRetry()) {
          <button type="button" class="retry" (click)="retry.emit()">تلاش دوباره</button>
        }
        <button type="button" class="dismiss" aria-label="بستن" (click)="dismiss.emit()">
          &times;
        </button>
      </div>
    </div>
  `,
  styles: `
    .banner {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-4);
      background: var(--danger-soft);
      border: 1px solid var(--danger-border);
      border-radius: var(--radius-md);
      color: var(--danger);
      font-size: var(--text-sm);
      max-width: var(--content-measure);
    }
    .text {
      flex: 1;
      line-height: var(--leading-tight);
    }
    .actions {
      display: flex;
      align-items: center;
      gap: var(--space-1);
      flex-shrink: 0;
    }
    .retry {
      padding: var(--space-1) var(--space-3);
      border-radius: var(--radius-sm);
      border: 1px solid var(--danger-border);
      color: var(--danger);
      font-size: var(--text-xs);
      font-weight: 600;
      transition: background var(--transition-fast);
    }
    .retry:hover {
      background: color-mix(in srgb, var(--danger) 12%, transparent);
    }
    .dismiss {
      width: 26px;
      height: 26px;
      border-radius: var(--radius-sm);
      font-size: 1.15rem;
      line-height: 1;
      color: var(--danger);
      opacity: 0.7;
    }
    .dismiss:hover {
      opacity: 1;
    }
    .pop {
      animation: pop var(--transition) both;
    }
    @keyframes pop {
      from {
        opacity: 0;
        transform: translateY(4px);
      }
    }
  `,
})
export class ErrorBanner {
  readonly message = input.required<string>();
  readonly canRetry = input(false);
  readonly retry = output<void>();
  readonly dismiss = output<void>();
}
