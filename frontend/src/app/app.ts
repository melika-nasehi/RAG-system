import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Rag, RagAnswer } from './services/rag';

@Component({
  selector: 'app-root',
  imports: [FormsModule],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected readonly question = signal('');
  protected readonly answer = signal<RagAnswer | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal('');

  constructor(private rag: Rag) {}

  ask() {
    const q = this.question().trim();
    if (!q) {
      return;
    }

    this.loading.set(true);
    this.error.set('');
    this.answer.set(null);

    this.rag.ask(q).subscribe({
      next: (result) => {
        this.answer.set(result);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set('خطا در ارتباط با سرور. مطمئن شوید Django در حال اجراست.');
        this.loading.set(false);
        console.error(err);
      }
    });
  }
}