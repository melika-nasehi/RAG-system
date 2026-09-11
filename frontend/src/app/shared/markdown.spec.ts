import { renderMarkdown } from './markdown';

describe('renderMarkdown', () => {
  it('wraps plain lines in paragraphs', () => {
    expect(renderMarkdown('یک خط')).toBe('<p>یک خط</p>');
  });

  it('renders bold and inline code', () => {
    expect(renderMarkdown('**پررنگ** و `کد`')).toBe(
      '<p><strong>پررنگ</strong> و <code>کد</code></p>',
    );
  });

  it('groups consecutive bullets into one list', () => {
    const html = renderMarkdown('- الف\n- ب\n- ج');
    expect(html).toBe('<ul><li>الف</li><li>ب</li><li>ج</li></ul>');
  });

  it('recognises Persian-numbered ordered lists', () => {
    const html = renderMarkdown('۱. اول\n۲. دوم');
    expect(html).toBe('<ol><li>اول</li><li>دوم</li></ol>');
  });

  it('escapes HTML before adding its own tags', () => {
    const html = renderMarkdown('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
    expect(html).not.toContain('<script>');
  });

  it('separates paragraphs on a blank line', () => {
    expect(renderMarkdown('یک\n\nدو')).toBe('<p>یک</p><p>دو</p>');
  });
});
