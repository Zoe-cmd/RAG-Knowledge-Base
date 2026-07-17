/**
 * 聊天消息 API（api-spec.md 4.3）。
 *
 * 发送消息端点为 SSE 流式，使用 fetch + ReadableStream 接收。
 * EventSource 不支持 POST，因此不使用浏览器原生 EventSource。
 *
 * SSE 事件协议见 api-spec.md 4.3.1 与 handoff-backend-to-frontend-ai.md 第 6 节。
 */
import { API_BASE_URL, SSE_EVENT } from '@/utils/constants';

/**
 * SSE 回调集合。
 * @typedef {Object} StreamCallbacks
 * @property {(references: Array) => void} [onReferences] - 引用来源事件
 * @property {(content: string) => void} [onToken] - 流式 token 事件
 * @property {(payload: {message_id: string, elapsed_ms: number}) => void} [onDone] - 完成事件
 * @property {(payload: {message: string, code: string}) => void} [onError] - 错误事件
 */

/**
 * 解析 SSE 流文本，按事件分发回调。
 * SSE 事件格式：
 *   event: {type}\n
 *   data: {json}\n\n
 *
 * @param {string} chunk - 文本块
 * @param {{currentEvent: string|null}} state - 解析状态（含当前事件名）
 * @param {StreamCallbacks} callbacks
 */
function processChunk(chunk, state, callbacks) {
  const lines = chunk.split('\n');
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      state.currentEvent = line.slice(7).trim();
    } else if (line.startsWith('data: ')) {
      const raw = line.slice(6);
      if (!state.currentEvent) continue;

      let data;
      try {
        data = raw.trim() === '' ? [] : JSON.parse(raw);
      } catch {
        // 忽略无法解析的 data 行（如 keep-alive 注释）
        continue;
      }

      switch (state.currentEvent) {
        case SSE_EVENT.REFERENCES:
          callbacks.onReferences?.(Array.isArray(data) ? data : []);
          break;
        case SSE_EVENT.TOKEN:
          callbacks.onToken?.(data?.content ?? '');
          break;
        case SSE_EVENT.DONE:
          callbacks.onDone?.(data);
          break;
        case SSE_EVENT.ERROR:
          callbacks.onError?.(data);
          break;
        default:
          break;
      }
      state.currentEvent = null;
    }
    // 事件分隔空行：event 与 data 成对出现，已在 data 处理后重置 currentEvent
  }
}

/**
 * 发送消息并接收 SSE 流式回答。
 *
 * @param {string} sessionId - 会话 ID
 * @param {string} question - 用户问题
 * @param {StreamCallbacks & {signal?: AbortSignal}} options - 回调与中断信号
 * @returns {Promise<void>} 流结束时 resolve；客户端中断时 resolve（不 reject）
 */
export async function streamChat(sessionId, question, options = {}) {
  const { signal, onReferences, onToken, onDone, onError } = options;
  const callbacks = { onReferences, onToken, onDone, onError };

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ session_id: sessionId, question }),
      signal,
    });
  } catch (fetchErr) {
    // AbortError：客户端主动中断，不视为错误
    if (fetchErr?.name === 'AbortError') {
      return;
    }
    callbacks.onError?.({
      code: 'LLM_CONNECTION_ERROR',
      message: '网络连接中断，请检查网络',
    });
    throw fetchErr;
  }

  if (!response.ok) {
    // 非 SSE 错误（如 404 会话不存在、422 校验失败）
    let code = 'INTERNAL_ERROR';
    let message = '请求失败';
    try {
      const body = await response.json();
      if (body?.error?.code) {
        code = body.error.code;
        message = body.error.message;
      } else if (body?.detail) {
        code = 'VALIDATION_ERROR';
        message = Array.isArray(body.detail)
          ? body.detail.map((d) => d.msg).join('; ')
          : String(body.detail);
      }
    } catch {
      // 响应体非 JSON，使用状态码推断
    }
    const err = { code, message };
    callbacks.onError?.(err);
    throw err;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const state = { currentEvent: null };
  let buffer = '';

  try {
    let streamDone = false;
    while (!streamDone) {
      const { done, value } = await reader.read();
      if (done) {
        streamDone = true;
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      // 按行切分，最后一段可能不完整，保留到 buffer
      const lastNewline = buffer.lastIndexOf('\n');
      if (lastNewline >= 0) {
        const complete = buffer.slice(0, lastNewline + 1);
        buffer = buffer.slice(lastNewline + 1);
        processChunk(complete, state, callbacks);
      }
    }
    // 处理剩余 buffer
    if (buffer.trim()) {
      processChunk(buffer, state, callbacks);
    }
  } catch (err) {
    // AbortError：客户端主动中断，不视为错误
    if (err?.name === 'AbortError') {
      return;
    }
    // 网络中断
    callbacks.onError?.({
      code: 'LLM_CONNECTION_ERROR',
      message: '网络连接中断，请检查网络',
    });
    throw err;
  }
}
