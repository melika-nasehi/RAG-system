import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthStore } from '../../state/auth-store';

const DEGREES = [
  { value: 'associate', label: 'کاردانی' },
  { value: 'bachelor', label: 'کارشناسی' },
  { value: 'master', label: 'کارشناسی ارشد' },
  { value: 'doctorate', label: 'دکتری' },
];

@Component({
  selector: 'app-register-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="wrap">
      <form class="card" (submit)="submit($event)">
        <div class="brand" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22">
            <path
              fill="currentColor"
              d="M12 3 3 7v2l9 4 7-3.1V15h2V7l-9-4Zm-6 9.2V16c0 1.7 2.7 3 6 3s6-1.3 6-3v-3.8l-6 2.6-6-2.6Z"
            />
          </svg>
        </div>
        <h1>ثبت‌نام دانشجو</h1>
        <p class="sub">برای پرسیدن سؤال، یک حساب دانشجویی بسازید</p>

        <label>
          نام کاربری
          <input name="username" [(ngModel)]="form.username" autocomplete="username" required />
        </label>
        <label>
          گذرواژه
          <input
            name="password"
            type="password"
            [(ngModel)]="form.password"
            autocomplete="new-password"
            required
          />
        </label>
        <label>
          ایمیل <span class="opt">(اختیاری)</span>
          <input name="email" type="email" [(ngModel)]="form.email" autocomplete="email" />
        </label>

        <div class="row">
          <label>
            مقطع
            <select name="degree" [(ngModel)]="form.degree_level" required>
              @for (d of degrees; track d.value) {
                <option [value]="d.value">{{ d.label }}</option>
              }
            </select>
          </label>
          <label>
            سال ورود
            <input
              name="year"
              type="number"
              [(ngModel)]="form.entry_year"
              placeholder="۱۴۰۲"
              required
            />
          </label>
        </div>
        <label>
          رشته تحصیلی <span class="opt">(اختیاری)</span>
          <input name="field" [(ngModel)]="form.field_of_study" />
        </label>

        @if (error()) {
          <p class="error" role="alert">{{ error() }}</p>
        }

        <button type="submit" [disabled]="busy()">
          {{ busy() ? 'در حال ثبت‌نام…' : 'ثبت‌نام' }}
        </button>

        <p class="switch">حساب دارید؟ <a routerLink="/login">وارد شوید</a></p>
      </form>
    </div>
  `,
  styleUrl: '../login-page/login-page.css',
})
export class RegisterPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);

  protected readonly degrees = DEGREES;
  protected form = {
    username: '',
    password: '',
    email: '',
    degree_level: 'bachelor',
    entry_year: null as number | null,
    field_of_study: '',
  };
  protected readonly busy = signal(false);
  protected readonly error = signal('');

  async submit(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');

    try {
      await this.auth.register({
        username: this.form.username.trim(),
        password: this.form.password,
        email: this.form.email.trim() || undefined,
        degree_level: this.form.degree_level,
        entry_year: Number(this.form.entry_year),
        field_of_study: this.form.field_of_study.trim() || undefined,
      });
      this.router.navigateByUrl('/');
    } catch (err) {
      this.error.set(this.messageFor(err));
    } finally {
      this.busy.set(false);
    }
  }

  private messageFor(err: unknown): string {
    if (err instanceof HttpErrorResponse && err.status === 400 && err.error) {
      const first = Object.values(err.error as Record<string, unknown>)[0];
      if (Array.isArray(first) && typeof first[0] === 'string') return first[0];
      if (typeof first === 'string') return first;
    }
    return 'ثبت‌نام ناموفق بود. لطفاً دوباره تلاش کنید.';
  }
}
