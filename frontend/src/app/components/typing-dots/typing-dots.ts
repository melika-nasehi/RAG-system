import { ChangeDetectionStrategy, Component } from '@angular/core';

/** The "assistant is thinking" indicator. The request is not streamed, so
 *  this stands in for the whole round-trip. */
@Component({
  selector: 'app-typing-dots',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span class="dots" role="status" aria-label="در حال آماده‌سازی پاسخ">
      <span></span><span></span><span></span>
    </span>
  `,
  styles: `
    .dots {
      display: inline-flex;
      gap: 5px;
      align-items: center;
      padding: var(--space-1) 0;
    }
    .dots span {
      width: 7px;
      height: 7px;
      border-radius: var(--radius-full);
      background: var(--text-muted);
      animation: blink 1.3s ease-in-out infinite;
    }
    .dots span:nth-child(2) {
      animation-delay: 0.18s;
    }
    .dots span:nth-child(3) {
      animation-delay: 0.36s;
    }
    @keyframes blink {
      0%,
      70%,
      100% {
        opacity: 0.25;
        transform: translateY(0);
      }
      35% {
        opacity: 1;
        transform: translateY(-3px);
      }
    }
  `,
})
export class TypingDots {}
