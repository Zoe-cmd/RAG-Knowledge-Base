/**
 * 消息提示工具。
 *
 * 封装 ElMessage，统一错误码 → 友好文案映射。
 */
import { ElMessage } from 'element-plus';
import { ERROR_MESSAGE_MAP } from './constants';

/**
 * 根据错误对象显示错误提示。
 * @param {{code?: string, message?: string}|Error} error
 * @param {string} [fallback] - 兜底文案
 */
export function showError(error, fallback) {
  const code = error?.code;
  const message =
    error?.message ||
    (code ? ERROR_MESSAGE_MAP[code] : null) ||
    fallback ||
    ERROR_MESSAGE_MAP.INTERNAL_ERROR;
  ElMessage.error(message);
}

/**
 * 成功提示。
 * @param {string} message
 */
export function showSuccess(message) {
  ElMessage.success(message);
}

/**
 * 警告提示。
 * @param {string} message
 */
export function showWarning(message) {
  ElMessage.warning(message);
}
