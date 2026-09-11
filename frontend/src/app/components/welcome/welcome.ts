import { ChangeDetectionStrategy, Component, output } from '@angular/core';

const EXAMPLES = [
  'حداکثر واحد درسی مجاز در هر نیمسال چند است؟',
  'شرایط و مدارک لازم برای مرخصی تحصیلی چیست؟',
  'دانشجو در چه صورتی مشروط محسوب می‌شود؟',
  'ضوابط استفاده از هوش مصنوعی در تکالیف درسی چیست؟',
];

/** Shown before the first question. Gives the assistant an identity and a
 *  few concrete prompts, so a new user is not staring at an empty box. */
@Component({
  selector: 'app-welcome',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="welcome" animate.enter="fade">
      <div class="mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="26" height="26">
          <path
            fill="currentColor"
            d="M12 3 3 7v2l9 4 7-3.1V15h2V7l-9-4Zm-6 9.2V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-3.8l-6 2.6-6-2.6Z"
          />
        </svg>
      </div>
      <h2>دستیار مقررات دانشجویی</h2>
      <p class="lead">
        پرسش خود را درباره آیین‌نامه‌ها و مقررات آموزشی بپرسید. پاسخ‌ها تنها بر پایهٔ
        متن اسناد رسمی و همراه با ذکر منبع و شمارهٔ صفحه ارائه می‌شود.
      </p>

      <div class="examples">
        @for (example of examples; track example) {
          <button type="button" class="chip" (click)="pick.emit(example)">
            {{ example }}
          </button>
        }
      </div>
    </div>
  `,
  styles: `
    .welcome {
      margin: auto;
      max-width: 42rem;
      text-align: center;
      padding: var(--space-6) var(--space-4);
    }
    .mark {
      width: 56px;
      height: 56px;
      margin: 0 auto var(--space-4);
      border-radius: var(--radius-lg);
      display: grid;
      place-items: center;
      background: var(--accent-soft);
      color: var(--accent);
    }
    h2 {
      font-size: var(--text-xl);
      font-weight: 700;
      margin-bottom: var(--space-3);
    }
    .lead {
      color: var(--text-secondary);
      line-height: var(--leading-relaxed);
      font-size: var(--text-base);
      margin-bottom: var(--space-6);
    }
    .examples {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: var(--space-2);
    }
    .chip {
      text-align: start;
      padding: var(--space-3) var(--space-4);
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: var(--text-sm);
      line-height: var(--leading-tight);
      transition: border-color var(--transition-fast), background var(--transition-fast),
        transform var(--transition-fast);
    }
    .chip:hover {
      border-color: var(--accent);
      background: var(--surface-hover);
      color: var(--text-primary);
      transform: translateY(-1px);
    }
    .fade {
      animation: fade var(--transition-slow) both;
    }
    @keyframes fade {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
    }
    @media (max-width: 560px) {
      .examples {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class Welcome {
  readonly examples = EXAMPLES;
  readonly pick = output<string>();
}
