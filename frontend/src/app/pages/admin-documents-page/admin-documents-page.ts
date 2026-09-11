import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { AdminApi, type CorpusDocument, type UploadResult } from '../../services/admin';
import { toPersianDigits, timeAgo } from '../../shared/persian';

const VERDICT_LABEL: Record<string, string> = {
  ACCEPT: 'پذیرفته‌شده',
  REPAIR: 'اصلاح‌شده',
};

@Component({
  selector: 'app-admin-documents-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="page">
      <header class="bar">
        <a routerLink="/" class="back" aria-label="بازگشت به گفتگو">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" d="m15 5-7 7 7 7" />
          </svg>
        </a>
        <h1>مدیریت اسناد</h1>
      </header>

      <section class="upload">
        <h2>افزودن سند جدید</h2>
        <p class="hint">
          فایل PDF از اعتبارسنجی عبور می‌کند؛ در صورت پذیرش، به‌صورت خودکار تکه‌بندی و
          نمایه می‌شود. این کار ممکن است چند ده ثانیه طول بکشد.
        </p>

        <label class="picker">
          <input type="file" accept="application/pdf,.pdf" (change)="pick($event)" [disabled]="busy()" />
          <span>{{ fileName() || 'انتخاب فایل PDF' }}</span>
        </label>

        <button type="button" (click)="upload()" [disabled]="!file() || busy()">
          {{ busy() ? 'در حال پردازش…' : 'بارگذاری و نمایه‌سازی' }}
        </button>

        @if (result(); as r) {
          <div class="result" [class.ok]="r.accepted" [class.bad]="!r.accepted" role="status">
            @if (r.accepted) {
              <strong>«{{ r.source }}» پذیرفته شد.</strong>
              <span>
                {{ fa(r.chunks_added ?? 0) }} تکه به نمایه افزوده شد
                (مجموع {{ fa(r.chunks_total ?? 0) }})@if (r.digits_repaired) {، ارقام معکوس اصلاح شد}.
              </span>
            } @else {
              <strong>«{{ r.source }}» رد شد.</strong>
              <span>{{ r.reason }}</span>
            }
          </div>
        }
      </section>

      <section class="list">
        <h2>اسناد موجود <span class="count">{{ fa(documents().length) }}</span></h2>

        @if (deleteError()) {
          <p class="delete-error" role="alert">{{ deleteError() }}</p>
        }

        @if (loading()) {
          <p class="muted">در حال بارگذاری…</p>
        } @else if (documents().length === 0) {
          <p class="muted">هنوز سندی نمایه نشده است.</p>
        } @else {
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>نام فایل</th>
                  <th>تاریخ بارگذاری</th>
                  <th>وضعیت</th>
                  <th>بارگذاری‌کننده</th>
                  <th>صفحات</th>
                  <th>تکه‌ها</th>
                  <th class="actions-col"></th>
                </tr>
              </thead>
              <tbody>
                @for (doc of documents(); track doc.id) {
                  <tr>
                    <td class="name" [title]="doc.source">{{ doc.source }}</td>
                    <td class="muted-cell">{{ ago(doc.uploaded_at) }}</td>
                    <td>
                      <span class="verdict" [class.repair]="doc.verdict === 'REPAIR'">
                        {{ verdictLabel(doc.verdict) }}
                      </span>
                    </td>
                    <td class="muted-cell">{{ doc.uploaded_by || '—' }}</td>
                    <td class="muted-cell">{{ doc.page_count ? fa(doc.page_count) : '—' }}</td>
                    <td class="muted-cell">{{ fa(doc.chunk_count) }}</td>
                    <td class="actions">
                      <button
                        type="button"
                        class="icon-btn"
                        aria-label="دانلود «{{ doc.source }}»"
                        [disabled]="busyId() === doc.id"
                        (click)="download(doc)"
                      >
                        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                          <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 3v12m0 0-4-4m4 4 4-4M5 19h14" />
                        </svg>
                      </button>

                      @if (confirmingDeleteId() === doc.id) {
                        <button type="button" class="icon-btn danger" aria-label="تأیید حذف" (click)="confirmDelete(doc.id)">
                          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                            <path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" d="m5 12 5 5 9-10" />
                          </svg>
                        </button>
                        <button type="button" class="icon-btn" aria-label="انصراف" (click)="cancelDelete()">
                          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                            <path fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" d="m6 6 12 12M18 6 6 18" />
                          </svg>
                        </button>
                      } @else {
                        <button
                          type="button"
                          class="icon-btn"
                          aria-label="حذف «{{ doc.source }}»"
                          [disabled]="busyId() === doc.id"
                          (click)="askDelete(doc.id)"
                        >
                          <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
                            <path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2m2 0-.7 12.1a2 2 0 0 1-2 1.9H9.7a2 2 0 0 1-2-1.9L7 7h10Z" />
                          </svg>
                        </button>
                      }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </section>
    </div>
  `,
  styleUrl: './admin-documents-page.css',
})
export class AdminDocumentsPage {
  private readonly api = inject(AdminApi);
  protected readonly fa = toPersianDigits;
  protected readonly ago = timeAgo;

  protected readonly documents = signal<CorpusDocument[]>([]);
  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly file = signal<File | null>(null);
  protected readonly fileName = signal('');
  protected readonly result = signal<UploadResult | null>(null);

  // Delete goes through the same "ask, then confirm" step as the sidebar's
  // conversation delete — a stray click on a permanent, indexed document
  // shouldn't remove it outright.
  protected readonly confirmingDeleteId = signal<number | null>(null);
  protected readonly busyId = signal<number | null>(null);
  protected readonly deleteError = signal<string | null>(null);

  constructor() {
    this.refresh();
  }

  protected verdictLabel(verdict: string): string {
    return VERDICT_LABEL[verdict] ?? verdict;
  }

  private refresh(): void {
    this.loading.set(true);
    this.api.listDocuments().subscribe({
      next: (docs) => {
        this.documents.set(docs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  pick(event: Event): void {
    const chosen = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.file.set(chosen);
    this.fileName.set(chosen?.name ?? '');
    this.result.set(null);
  }

  upload(): void {
    const file = this.file();
    if (!file || this.busy()) return;
    this.busy.set(true);
    this.result.set(null);

    this.api.uploadDocument(file).subscribe({
      next: (res) => {
        this.result.set(res);
        this.busy.set(false);
        this.file.set(null);
        this.fileName.set('');
        if (res.accepted) this.refresh();
      },
      error: (err: unknown) => {
        this.busy.set(false);
        if (err instanceof HttpErrorResponse && err.error && typeof err.error === 'object') {
          this.result.set(err.error as UploadResult);
        } else {
          this.result.set({
            accepted: false,
            source: file.name,
            reason: 'بارگذاری ناموفق بود. اتصال شبکه را بررسی کنید.',
          });
        }
      },
    });
  }

  download(doc: CorpusDocument): void {
    if (this.busyId()) return;
    this.busyId.set(doc.id);
    this.api.downloadDocument(doc.id, doc.source).subscribe({
      next: () => this.busyId.set(null),
      error: () => {
        this.busyId.set(null);
        this.deleteError.set('دانلود فایل ناموفق بود.');
      },
    });
  }

  askDelete(id: number): void {
    this.deleteError.set(null);
    this.confirmingDeleteId.set(id);
  }

  cancelDelete(): void {
    this.confirmingDeleteId.set(null);
  }

  confirmDelete(id: number): void {
    this.confirmingDeleteId.set(null);
    this.busyId.set(id);
    this.deleteError.set(null);

    this.api.deleteDocument(id).subscribe({
      next: () => {
        this.documents.update((docs) => docs.filter((d) => d.id !== id));
        this.busyId.set(null);
      },
      error: () => {
        this.busyId.set(null);
        this.deleteError.set('حذف سند ناموفق بود. دوباره تلاش کنید.');
      },
    });
  }
}
