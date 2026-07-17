/**
 * 配置相关 API（api-spec.md 4.4）。
 *
 * - 获取当前配置与统计
 * - 切换 Embedding Provider
 */
import request from './request';

/**
 * 获取当前配置与统计信息。
 * @returns {Promise<object>} 配置对象（含 statistics）
 */
export function getConfig() {
  return request.get('/config');
}

/**
 * 切换 Embedding Provider。
 * @param {string} provider - openai / bge
 * @returns {Promise<object>} 切换结果（含 needs_reindex 等）
 */
export function switchEmbeddingProvider(provider) {
  return request.put('/config/embedding-provider', { provider });
}
