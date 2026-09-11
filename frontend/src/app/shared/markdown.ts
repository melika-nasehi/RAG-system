/** A deliberately small Markdown renderer.
 *
 *  The model's answers use only a narrow slice of Markdown — paragraphs,
 *  bold, and bulleted or numbered lists for multi-part regulations — so a
 *  full parser (and its dependency, which we cannot install here) is not
 *  warranted. Everything is HTML-escaped before any tag is introduced, and
 *  the result still passes through Angular's DOM sanitizer at the binding.
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function inline(text: string): string {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*(?!\s)([^*]+?)\*(?!\*)/g, '$1<em>$2</em>')
    .replace(/`([^`]+?)`/g, '<code>$1</code>');
}

type Block =
  | { kind: 'p'; lines: string[] }
  | { kind: 'ul'; items: string[] }
  | { kind: 'ol'; items: string[] }
  | { kind: 'h'; level: number; text: string };

const BULLET = /^\s*[-*•]\s+(.*)$/;
const ORDERED = /^\s*(?:\d+|[۰-۹]+)[.)]\s+(.*)$/;
const HEADING = /^\s*(#{1,4})\s+(.*)$/;

export function renderMarkdown(source: string): string {
  const blocks: Block[] = [];

  for (const rawLine of source.replace(/\r\n/g, '\n').split('\n')) {
    const line = rawLine.trimEnd();
    const last = blocks[blocks.length - 1];

    if (line.trim() === '') {
      if (last?.kind === 'p') blocks.push({ kind: 'p', lines: [] });
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) {
      blocks.push({ kind: 'h', level: heading[1].length, text: heading[2] });
      continue;
    }

    const bullet = line.match(BULLET);
    if (bullet) {
      if (last?.kind === 'ul') last.items.push(bullet[1]);
      else blocks.push({ kind: 'ul', items: [bullet[1]] });
      continue;
    }

    const ordered = line.match(ORDERED);
    if (ordered) {
      if (last?.kind === 'ol') last.items.push(ordered[1]);
      else blocks.push({ kind: 'ol', items: [ordered[1]] });
      continue;
    }

    if (last?.kind === 'p' && last.lines.length) last.lines.push(line);
    else blocks.push({ kind: 'p', lines: [line] });
  }

  return blocks
    .filter((b) => b.kind !== 'p' || b.lines.length > 0)
    .map((block) => {
      switch (block.kind) {
        case 'h':
          return `<h${block.level}>${inline(block.text)}</h${block.level}>`;
        case 'ul':
          return `<ul>${block.items.map((i) => `<li>${inline(i)}</li>`).join('')}</ul>`;
        case 'ol':
          return `<ol>${block.items.map((i) => `<li>${inline(i)}</li>`).join('')}</ol>`;
        case 'p':
          return `<p>${block.lines.map(inline).join('<br>')}</p>`;
      }
    })
    .join('');
}
