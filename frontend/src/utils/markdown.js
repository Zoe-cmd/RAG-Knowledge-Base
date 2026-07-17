/**
 * Markdown 渲染工具。
 *
 * 使用 marked 解析 Markdown，highlight.js 代码高亮，
 * DOMPurify 净化 HTML 防 XSS（安全审计重点项）。
 *
 * 用于 AI 回答内容的渲染（design-system.md 7.3）。
 */
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js/lib/common';

// 配置 marked：开启 GFM、换行转 <br>、代码高亮
marked.setOptions({
  gfm: true,
  breaks: true,
});

/**
 * 自定义 renderer：为代码块添加语言标识与 highlight.js 高亮。
 */
const renderer = new marked.Renderer();

const originalCode = renderer.code.bind(renderer);
renderer.code = (code, language) => {
  const lang = (language || '').toLowerCase();
  const codeText = typeof code === 'string' ? code : code?.text ?? '';
  try {
    if (lang && hljs.getLanguage(lang)) {
      const highlighted = hljs.highlight(codeText, { language: lang }).value;
      return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`;
    }
    const auto = hljs.highlightAuto(codeText).value;
    return `<pre><code class="hljs">${auto}</code></pre>`;
  } catch {
    return originalCode(code, language);
  }
};

marked.use({ renderer });

/**
 * 将 Markdown 文本渲染为安全的 HTML。
 * @param {string} markdown - Markdown 原文
 * @returns {string} 净化后的 HTML
 */
export function renderMarkdown(markdown) {
  if (!markdown) return '';
  const rawHtml = marked.parse(markdown);
  // 净化：移除脚本、事件处理器等危险内容
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: [
      'p', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
      'a', 'strong', 'em', 'del', 's', 'sup', 'sub',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'span', 'div', 'img',
    ],
    ALLOWED_ATTR: ['href', 'title', 'src', 'alt', 'class', 'target', 'rel'],
  });
}
