/**
 * 会话相关 API（api-spec.md 4.2）。
 *
 * - 新建会话
 * - 获取会话列表
 * - 删除单个会话
 * - 清空所有会话
 * - 获取会话消息列表
 */
import request from './request';

/**
 * 新建会话。
 * @returns {Promise<object>} 会话对象
 */
export function createSession() {
  return request.post('/chat/sessions', {});
}

/**
 * 获取会话列表。
 * @returns {Promise<Array>} 会话数组
 */
export function getSessions() {
  return request.get('/chat/sessions');
}

/**
 * 删除单个会话。
 * @param {string} id - 会话 ID
 * @returns {Promise<void>}
 */
export function deleteSession(id) {
  return request.delete(`/chat/sessions/${id}`);
}

/**
 * 清空所有会话。
 * @returns {Promise<{deleted_count: number}>}
 */
export function clearAllSessions() {
  return request.delete('/chat/sessions');
}

/**
 * 获取会话消息列表。
 * @param {string} sessionId - 会话 ID
 * @returns {Promise<{messages: Array}>}
 */
export function getSessionMessages(sessionId) {
  return request.get(`/chat/sessions/${sessionId}/messages`);
}
