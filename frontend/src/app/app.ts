import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AuthStore } from './state/auth-store';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet],
  template: `
    @if (auth.ready()) {
      <router-outlet />
    } @else {
      <div class="splash" role="status" aria-label="در حال بارگذاری">
        <span class="spinner"></span>
      </div>
    }
  `,
  styles: `
    :host {
      display: block;
      height: 100dvh;
    }
    .splash {
      height: 100%;
      display: grid;
      place-items: center;
      background: var(--bg);
    }
    .spinner {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 3px solid var(--border-strong);
      border-top-color: var(--accent);
      animation: spin 0.8s linear infinite;
    }
    @keyframes spin {
      to {
        transform: rotate(360deg);
      }
    }
  `,
})
export class App {
  protected readonly auth = inject(AuthStore);

  constructor() {
    // Confirm any stored session before the first guarded route resolves.
    void this.auth.ensureRestored();
  }
}
