import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AuthStore } from '../../state/auth-store';

@Component({
  selector: 'app-login-page',
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
        <h1>ورود به سامانه</h1>
        <p class="sub">سامانه پرسش‌وپاسخ مقررات دانشجویی</p>

        <label>
          نام کاربری
          <input name="username" [(ngModel)]="username" autocomplete="username" required />
        </label>
        <label>
          گذرواژه
          <input
            name="password"
            type="password"
            [(ngModel)]="password"
            autocomplete="current-password"
            required
          />
        </label>

        @if (error()) {
          <p class="error" role="alert">{{ error() }}</p>
        }

        <button type="submit" [disabled]="busy()">
          {{ busy() ? 'در حال ورود…' : 'ورود' }}
        </button>

        <p class="switch">
          حساب ندارید؟ <a routerLink="/register">ثبت‌نام کنید</a>
        </p>
      </form>
    </div>
  `,
  styleUrl: './login-page.css',
})
export class LoginPage {
  private readonly auth = inject(AuthStore);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected username = '';
  protected password = '';
  protected readonly busy = signal(false);
  protected readonly error = signal('');

  async submit(event: Event): Promise<void> {
    event.preventDefault();
    if (this.busy()) return;
    this.busy.set(true);
    this.error.set('');

    try {
      await this.auth.login(this.username.trim(), this.password);
      const next = this.route.snapshot.queryParamMap.get('next') || '/';
      this.router.navigateByUrl(next);
    } catch (err) {
      this.error.set(
        err instanceof HttpErrorResponse && err.status === 401
          ? 'نام کاربری یا گذرواژه نادرست است.'
          : 'ورود ناموفق بود. اتصال شبکه را بررسی کنید.',
      );
    } finally {
      this.busy.set(false);
    }
  }
}
