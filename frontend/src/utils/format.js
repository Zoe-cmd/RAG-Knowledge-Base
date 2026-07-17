/**
 * 格式化工具函数。
 *
 * 文件大小、日期时间、相对时间等格式化，
 * 供列表与消息组件复用。
 */

/**
 * 格式化文件大小为人类可读字符串。
 * @param {number} bytes - 文件字节数
 * @returns {string} 格式化后的大小，如 "2.3 MB"
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / Math.pow(1024, index);
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`;
}

/**
 * 格式化 ISO 时间字符串为本地时间。
 * @param {string|null} isoString - ISO 8601 时间字符串
 * @param {string} format - 格式模板，默认 'YYYY-MM-DD HH:MM'
 * @returns {string} 格式化后的时间，空值返回 '-'
 */
export function formatDateTime(isoString, format = 'YYYY-MM-DD HH:MM') {
  if (!isoString) return '-';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return '-';

  const pad = (n) => String(n).padStart(2, '0');
  const map = {
    YYYY: date.getFullYear(),
    MM: pad(date.getMonth() + 1),
    DD: pad(date.getDate()),
    HH: pad(date.getHours()),
    MI: pad(date.getMinutes()),
    SS: pad(date.getSeconds()),
    MM_: pad(date.getMinutes()),
  };
  return format
    .replace('YYYY', map.YYYY)
    .replace('MM', map.MM)
    .replace('DD', map.DD)
    .replace('HH', map.HH)
    .replace('MI', map.MI)
    .replace('SS', map.SS);
}

/**
 * 格式化相对时间（如 "3 分钟前"）。
 * 超过 7 天则返回绝对时间。
 * @param {string|null} isoString - ISO 8601 时间字符串
 * @returns {string} 相对时间
 */
export function formatRelativeTime(isoString) {
  if (!isoString) return '-';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return '-';

  const diff = Date.now() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return '刚刚';
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;
  return formatDateTime(isoString, 'MM-DD HH:MM');
}

/**
 * 截断文本并添加省略号。
 * @param {string} text - 原文本
 * @param {number} maxLen - 最大长度
 * @returns {string} 截断后的文本
 */
export function truncate(text, maxLen = 20) {
  if (!text) return '';
  return text.length > maxLen ? `${text.slice(0, maxLen)}...` : text;
}

/**
 * 从文件名提取扩展名（小写）。
 * @param {string} filename - 文件名
 * @returns {string} 扩展名（不含点），如 "pdf"
 */
export function getFileExtension(filename) {
  if (!filename) return '';
  const index = filename.lastIndexOf('.');
  return index >= 0 ? filename.slice(index + 1).toLowerCase() : '';
}

/**
 * 格式化耗时（毫秒）为人类可读。
 * @param {number|null} ms - 毫秒数
 * @returns {string} 如 "3.2s"
 */
export function formatElapsed(ms) {
  if (ms == null) return '';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
