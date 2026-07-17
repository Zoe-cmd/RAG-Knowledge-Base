/**
 * 全局常量定义。
 *
 * 对应 api-spec.md 与 design-system.md 中的业务规则与状态映射。
 * 避免魔法数字/字符串，集中管理。
 */

// ===== API 基础路径（DEC-015: 开发环境通过 Vite Proxy）=====
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// ===== 文件类型 =====
export const FILE_TYPES = {
  PDF: 'pdf',
  DOCX: 'docx',
  MD: 'md',
  TXT: 'txt',
};

// 允许上传的文件类型及扩展名
export const ACCEPTED_FILE_TYPES = ['pdf', 'docx', 'md', 'txt'];

// 文件类型 → Element Plus 图标颜色（design-system.md 8）
export const FILE_TYPE_COLOR = {
  pdf: '#F56C6C',
  docx: '#409EFF',
  md: '#67C23A',
  txt: '#909399',
};

// 文件类型 → 中文标签
export const FILE_TYPE_LABEL = {
  pdf: 'PDF',
  docx: 'Word',
  md: 'Markdown',
  txt: 'TXT',
};

// ===== 业务限制（api-spec.md BR-DOC-002 / BR-DOC-003）=====
export const MAX_FILE_SIZE_MB = 20;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const MAX_DOCUMENTS = 100;

// 问答字数限制（api-spec.md 4.3.1）
export const QUESTION_MIN_LENGTH = 1;
export const QUESTION_MAX_LENGTH = 2000;

// ===== 文档处理状态（api-spec.md 5.1）=====
export const DOCUMENT_STATUS = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

// 状态标签映射（design-system.md 7.7）
export const STATUS_TAG_MAP = {
  pending: { type: 'warning', label: '等待中' },
  processing: { type: 'warning', label: '解析中' },
  completed: { type: 'success', label: '完成' },
  failed: { type: 'danger', label: '失败' },
};

// ===== 消息角色 =====
export const MESSAGE_ROLE = {
  USER: 'user',
  ASSISTANT: 'assistant',
};

// ===== SSE 事件类型（api-spec.md 4.3.1）=====
export const SSE_EVENT = {
  REFERENCES: 'references',
  TOKEN: 'token',
  DONE: 'done',
  ERROR: 'error',
};

// ===== 错误码 → 用户友好提示（api-spec.md 第 6 节）=====
export const ERROR_MESSAGE_MAP = {
  VALIDATION_ERROR: '请求参数有误，请检查后重试',
  DOCUMENT_NOT_FOUND: '文档不存在，可能已被删除',
  SESSION_NOT_FOUND: '会话不存在，可能已被删除',
  DOCUMENT_LIMIT_EXCEEDED: `文档数量已达上限 ${MAX_DOCUMENTS}，请先删除旧文档`,
  FILE_TOO_LARGE: `文件超过 ${MAX_FILE_SIZE_MB}MB 限制`,
  UNSUPPORTED_FILE_TYPE: '不支持的文件类型，仅支持 PDF、Word、Markdown、TXT',
  SCANNED_PDF: '该 PDF 疑似扫描件，MVP 版本暂不支持 OCR，请上传文本型 PDF',
  REINDEX_REQUIRED: '切换方案需要重建索引，请重新上传文档',
  LLM_TIMEOUT: '回答生成超时，请重试',
  LLM_AUTH_ERROR: 'API Key 无效，请检查 .env 配置',
  LLM_CONNECTION_ERROR: '网络连接异常，请检查网络或后端服务',
  EMBEDDING_ERROR: '问题向量化失败，请重试',
  INTERNAL_ERROR: '服务器内部错误，请稍后重试',
  SERVICE_UNAVAILABLE: '后端服务不可用，请确认服务已启动',
  NETWORK_ERROR: '网络错误，请检查后端服务是否运行',
};

// ===== Embedding Provider 选项 =====
export const EMBEDDING_PROVIDERS = [
  { value: 'openai', label: 'OpenAI', dimension: 1536, desc: 'text-embedding-3-small（在线）' },
  { value: 'bge', label: 'BGE bge-m3', dimension: 1024, desc: '本地模型（首次加载需下载）' },
];

// ===== 文档列表分页默认值 =====
export const DEFAULT_PAGE_SIZE = 20;

// 处理中文档轮询间隔（毫秒）
export const PROCESSING_POLL_INTERVAL = 3000;
