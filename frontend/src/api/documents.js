/**
 * 文档相关 API（api-spec.md 4.1）。
 *
 * - 上传文档（批量，multipart/form-data）
 * - 获取文档列表（分页）
 * - 删除文档
 */
import request from './request';

/**
 * 上传文档。
 * @param {File[]} files - 文件数组
 * @param {(percent: number) => void} [onProgress] - 上传进度回调
 * @returns {Promise<{documents: Array, failed: Array}>} 上传结果
 */
export function uploadDocuments(files, onProgress) {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // 大文件上传允许更长时间
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    },
  });
}

/**
 * 获取文档列表（分页）。
 * @param {{page?: number, size?: number, status?: string}} params
 * @returns {Promise<{data: Array, meta: {pagination: object}}>}
 */
export function getDocuments(params = {}) {
  return request.get('/documents', { params });
}

/**
 * 删除文档。
 * @param {string} id - 文档 ID
 * @returns {Promise<void>}
 */
export function deleteDocument(id) {
  return request.delete(`/documents/${id}`);
}
