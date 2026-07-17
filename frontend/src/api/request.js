/**
 * Axios 实例与拦截器。
 *
 * 响应拦截器统一处理：
 * 1. 成功响应：直接返回 response.data（即 { data, meta } 结构，见 api-spec.md 1.3）
 * 2. 错误响应：归一化为 { code, message, details } 并 reject
 *    - 兼容本项目统一错误格式（error.code）
 *    - 兼容 FastAPI 422 标准校验格式（detail 数组）
 *    - 兼容网络错误（无 response）
 */
import axios from 'axios';
import { ElMessage } from 'element-plus';
import { API_BASE_URL, ERROR_MESSAGE_MAP } from '@/utils/constants';

/**
 * 规范化错误对象。
 * @param {{code?: string, message?: string, details?: unknown}} errInfo
 * @returns {{code: string, message: string, details: unknown}}
 */
function normalizeError(errInfo) {
  return {
    code: errInfo.code || 'INTERNAL_ERROR',
    message: errInfo.message || ERROR_MESSAGE_MAP.INTERNAL_ERROR,
    details: errInfo.details || [],
  };
}

const request = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：可在此注入 traceId 等（MVP 暂无鉴权，DEC-001）
request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

// 响应拦截器：统一处理成功与错误
request.interceptors.response.use(
  // 成功：返回 { data, meta } 结构
  (response) => response.data,
  (error) => {
    const errData = error.response?.data;
    let normalized;

    if (errData?.error?.code) {
      // 本项目统一错误格式（api-spec.md 1.3）
      normalized = normalizeError(errData.error);
    } else if (Array.isArray(errData?.detail) || typeof errData?.detail === 'string') {
      // FastAPI 标准校验错误（422）：detail 为数组或字符串
      const message = Array.isArray(errData.detail)
        ? errData.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
        : errData.detail;
      normalized = normalizeError({
        code: 'VALIDATION_ERROR',
        message: message || ERROR_MESSAGE_MAP.VALIDATION_ERROR,
        details: errData.detail,
      });
    } else if (error.response) {
      // 有 HTTP 响应但非上述格式：按状态码归类
      const status = error.response.status;
      const code =
        status === 404
          ? 'NOT_FOUND'
          : status === 503
            ? 'SERVICE_UNAVAILABLE'
            : 'INTERNAL_ERROR';
      normalized = normalizeError({
        code,
        message: errData?.message || ERROR_MESSAGE_MAP[code] || ERROR_MESSAGE_MAP.INTERNAL_ERROR,
      });
    } else {
      // 无响应：网络错误
      normalized = normalizeError({
        code: 'NETWORK_ERROR',
        message: ERROR_MESSAGE_MAP.NETWORK_ERROR,
      });
    }

    // 非阻断式错误提示（调用方可通过 silent 选项关闭）
    if (!error.config?._silent) {
      ElMessage.error(normalized.message);
    }

    return Promise.reject(normalized);
  },
);

export default request;
