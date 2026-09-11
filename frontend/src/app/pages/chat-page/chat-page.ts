import { ChangeDetectionStrategy, Component, inject, viewChild } from '@angular/core';
import { ChatStore } from '../../state/chat-store';
import { Sidebar } from '../../components/sidebar/sidebar';
import { ChatHeader } from '../../components/chat-header/chat-header';
import { MessageList } from '../../components/message-list/message-list';
import { Composer } from '../../components/composer/composer';

@Component({
  selector: 'app-chat-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Sidebar, ChatHeader, MessageList, Composer],
  templateUrl: './chat-page.html',
  styleUrl: './chat-page.css',
  host: {
    '(document:keydown.escape)': 'store.closeDrawer()',
  },
})
export class ChatPage {
  protected readonly store = inject(ChatStore);
  private readonly composer = viewChild.required(Composer);

  /** An example chip was clicked — drop it into the composer, leaving the
   *  user to review and send. */
  protected onExample(text: string): void {
    this.composer().setText(text);
  }

  protected onSend(text: string): void {
    this.store.send(text);
  }
}
