import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';

/** The question box. Grows with its content up to a cap, sends on Enter,
 *  and inserts a newline on Shift+Enter. */
@Component({
  selector: 'app-composer',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="composer" (submit)="submit($event)">
      <div class="field">
        <textarea
          #box
          rows="1"
          [value]="text()"
          [disabled]="disabled()"
          placeholder="پرسش خود را بنویسید…"
          aria-label="متن پرسش"
          (input)="onInput($event)"
          (keydown.enter)="onEnter($event)"
        ></textarea>

        <button
          type="submit"
          class="send"
          [disabled]="disabled() || !text().trim()"
          aria-label="ارسال پرسش"
        >
          @if (disabled()) {
            <svg class="spin" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path
                fill="none"
                stroke="currentColor"
                stroke-width="2.5"
                stroke-linecap="round"
                d="M12 3a9 9 0 1 0 9 9"
              />
            </svg>
          } @else {
            <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
              <path fill="currentColor" d="M22 21 1 12l21-9v7L8 12l14 2v7Z" />
            </svg>
          }
        </button>
      </div>
      <p class="hint">پاسخ‌ها تنها از روی اسناد رسمی تولید می‌شوند و ممکن است کامل نباشند.</p>
    </form>
  `,
  styles: `
    .composer {
      padding: var(--space-3) var(--space-5) var(--space-4);
      background: var(--bg-elevated);
      border-top: 1px solid var(--border);
    }
    .field {
      display: flex;
      align-items: flex-end;
      gap: var(--space-2);
      max-width: var(--content-measure);
      margin: 0 auto;
      padding: var(--space-2);
      background: var(--surface);
      border: 1.5px solid var(--border-strong);
      border-radius: var(--radius-lg);
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
    }
    .field:focus-within {
      border-color: var(--accent);
      box-shadow: var(--ring);
    }
    textarea {
      flex: 1;
      border: none;
      background: none;
      resize: none;
      padding: var(--space-2) var(--space-2);
      max-height: 180px;
      line-height: var(--leading-normal);
      font-size: var(--text-base);
    }
    textarea:focus {
      outline: none;
    }
    textarea::placeholder {
      color: var(--text-muted);
    }
    .send {
      flex-shrink: 0;
      width: 38px;
      height: 38px;
      border-radius: var(--radius-md);
      display: grid;
      place-items: center;
      background: var(--accent);
      color: var(--text-on-accent);
      transition: background var(--transition-fast), opacity var(--transition-fast);
    }
    .send:hover:not(:disabled) {
      background: var(--accent-hover);
    }
    .send:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }
    .spin {
      animation: spin 0.9s linear infinite;
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
    .hint {
      max-width: var(--content-measure);
      margin: var(--space-2) auto 0;
      text-align: center;
      font-size: var(--text-xs);
      color: var(--text-muted);
    }
    @media (max-width: 720px) {
      .composer {
        padding: var(--space-2) var(--space-3) var(--space-3);
      }
      .hint {
        display: none;
      }
    }
  `,
})
export class Composer {
  readonly disabled = input(false);
  readonly send = output<string>();

  private readonly box = viewChild.required<ElementRef<HTMLTextAreaElement>>('box');
  readonly text = signal('');

  /** Called by the parent to drop an example question into the box. */
  setText(value: string): void {
    this.text.set(value);
    queueMicrotask(() => this.resize());
  }

  onInput(event: Event): void {
    this.text.set((event.target as HTMLTextAreaElement).value);
    this.resize();
  }

  onEnter(event: Event): void {
    const keyboard = event as KeyboardEvent;
    if (keyboard.shiftKey) return;
    event.preventDefault();
    this.emit();
  }

  submit(event: Event): void {
    event.preventDefault();
    this.emit();
  }

  private emit(): void {
    const value = this.text().trim();
    if (!value || this.disabled()) return;
    this.send.emit(value);
    this.text.set('');
    this.resize();
  }

  private resize(): void {
    const el = this.box().nativeElement;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }
}
