<script setup>
/**
 * 文档上传弹窗（design-system.md 7.6 / api-spec.md 4.1.1）。
 *
 * 功能：
 * - 拖拽 / 点击选择文件（批量）
 * - 前端预校验：文件类型、文件大小、文档总数
 * - 上传进度条
 * - 上传结果展示（成功 + 失败列表）
 *
 * 校验规则（BR-DOC-001 ~ BR-DOC-003）：
 * - 扩展名 ∈ {pdf, docx, md, txt}
 * - 单文件 ≤ 20MB
 * - 文档总数 < 100
 */
import { ref, computed, nextTick } from 'vue';
import { UploadFilled, Close, CircleCheckFilled, CircleCloseFilled } from '@element-plus/icons-vue';
import { useDocumentsStore } from '@/stores/documents';
import { useConfigStore } from '@/stores/config';
import { showError, showSuccess } from '@/utils/message';
import {
  ACCEPTED_FILE_TYPES,
  MAX_FILE_SIZE_MB,
  MAX_FILE_SIZE_BYTES,
  MAX_DOCUMENTS,
} from '@/utils/constants';
import { getFileExtension, formatFileSize } from '@/utils/format';

defineProps({
  /** 弹窗可见性（v-model） */
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const documentsStore = useDocumentsStore();
const configStore = useConfigStore();

/** el-upload 组件引用 */
const uploadRef = ref(null);
/** 待上传文件列表 [{ file, valid, error }] */
const pendingFiles = ref([]);
/** 上传结果 { documents: [], failed: [] } */
const uploadResult = ref(null);

/** accept 属性字符串 */
const acceptString = ACCEPTED_FILE_TYPES.map((ext) => `.${ext}`).join(',');

/** 有效文件列表 */
const validFiles = computed(() => pendingFiles.value.filter((f) => f.valid));
/** 无效文件数 */
const invalidCount = computed(() => pendingFiles.value.filter((f) => !f.valid).length);
/** 当前文档总数 */
const currentDocCount = computed(
  () => documentsStore.pagination.total || documentsStore.list.length,
);
/** 上传后是否超限 */
const wouldExceedLimit = computed(
  () => currentDocCount.value + validFiles.value.length > MAX_DOCUMENTS,
);
/** 是否处于上传中 */
const isUploading = computed(() => documentsStore.uploading);
/** 是否有上传结果 */
const hasResult = computed(() => uploadResult.value !== null);
/** 成功上传数 */
const successCount = computed(() => uploadResult.value?.documents?.length || 0);
/** 失败列表 */
const failedList = computed(() => uploadResult.value?.failed || []);

/** el-upload 文件变化回调 */
function handleFileChange(uploadFile) {
  const file = uploadFile.raw;
  if (!file) return;

  const ext = getFileExtension(file.name);
  let valid = true;
  let error = '';

  // 校验文件类型（BR-DOC-001）
  if (!ACCEPTED_FILE_TYPES.includes(ext)) {
    valid = false;
    error = `不支持的类型 .${ext}，仅支持 PDF/Word/MD/TXT`;
  }
  // 校验文件大小（BR-DOC-002）
  else if (file.size > MAX_FILE_SIZE_BYTES) {
    valid = false;
    error = `文件超过 ${MAX_FILE_SIZE_MB}MB 限制`;
  }

  // 去重（同名同大小视为重复）
  const isDuplicate = pendingFiles.value.some(
    (f) => f.file.name === file.name && f.file.size === file.size,
  );
  if (isDuplicate) {
    // 清除 el-upload 内部文件列表，避免重复触发
    nextTick(() => uploadRef.value?.clearFiles());
    return;
  }

  pendingFiles.value.push({ file, valid, error });

  // 清除 el-upload 内部文件列表（使用自定义列表管理）
  nextTick(() => uploadRef.value?.clearFiles());
}

/** 移除待上传文件 */
function handleRemoveFile(index) {
  pendingFiles.value.splice(index, 1);
}

/** 开始上传 */
async function handleUpload() {
  if (validFiles.value.length === 0) return;
  if (wouldExceedLimit.value) {
    showError(null, `文档数量将超过上限 ${MAX_DOCUMENTS}，请先删除旧文档`);
    return;
  }

  const files = validFiles.value.map((f) => f.file);
  try {
    const result = await documentsStore.upload(files);
    uploadResult.value = result;
    pendingFiles.value = [];
    // 刷新配置统计
    configStore.fetchConfig();
    const successNum = result.documents?.length || 0;
    const failedNum = result.failed?.length || 0;
    if (successNum > 0 && failedNum === 0) {
      showSuccess(`成功上传 ${successNum} 个文档`);
    }
  } catch (err) {
    showError(err, '上传失败');
  }
}

/** 继续上传（清除结果，回到选择文件状态） */
function handleContinue() {
  uploadResult.value = null;
}

/** 关闭弹窗 */
function handleClose() {
  pendingFiles.value = [];
  uploadResult.value = null;
  emit('update:modelValue', false);
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="上传文档"
    width="560px"
    :close-on-click-modal="!isUploading"
    :close-on-press-escape="!isUploading"
    :show-close="!isUploading"
    align-center
    @close="handleClose"
  >
    <!-- 上传结果 -->
    <div v-if="hasResult" class="upload-result">
      <div class="result-summary">
        <el-icon v-if="successCount > 0 && failedList.length === 0" class="result-icon success">
          <CircleCheckFilled />
        </el-icon>
        <el-icon v-else-if="failedList.length > 0" class="result-icon warning">
          <CircleCloseFilled />
        </el-icon>
        <span class="result-text">
          成功上传 {{ successCount }} 个文档
          <span v-if="failedList.length > 0">，{{ failedList.length }} 个失败</span>
        </span>
      </div>

      <!-- 失败列表 -->
      <div v-if="failedList.length > 0" class="failed-list">
        <div class="failed-title">失败文件：</div>
        <div v-for="(item, index) in failedList" :key="index" class="failed-item">
          <el-icon class="failed-icon"><CircleCloseFilled /></el-icon>
          <span class="failed-name" :title="item.filename">{{ item.filename }}</span>
          <span class="failed-error">{{ item.error }}</span>
        </div>
      </div>
    </div>

    <!-- 上传中 -->
    <div v-else-if="isUploading" class="upload-progress">
      <el-progress :percentage="documentsStore.uploadProgress" :stroke-width="8" status="success" />
      <p class="progress-text">正在上传文件...</p>
    </div>

    <!-- 选择文件 -->
    <div v-else class="upload-form">
      <el-upload
        ref="uploadRef"
        drag
        multiple
        :auto-upload="false"
        :show-file-list="false"
        :accept="acceptString"
        :on-change="handleFileChange"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="upload-tip">
            支持 PDF、Word(docx)、Markdown、TXT 格式，单文件 ≤
            {{ MAX_FILE_SIZE_MB }}MB，文档总数 ≤ {{ MAX_DOCUMENTS }} 个
          </div>
        </template>
      </el-upload>

      <!-- 待上传文件列表 -->
      <div v-if="pendingFiles.length > 0" class="pending-list">
        <div class="pending-header">
          <span>已选 {{ pendingFiles.length }} 个文件</span>
          <span v-if="invalidCount > 0" class="invalid-count">{{ invalidCount }} 个无效</span>
        </div>
        <div class="pending-items">
          <div
            v-for="(item, index) in pendingFiles"
            :key="index"
            class="pending-item"
            :class="{ invalid: !item.valid }"
          >
            <div class="pending-item-info">
              <span class="pending-name" :title="item.file.name">{{ item.file.name }}</span>
              <span class="pending-size">{{ formatFileSize(item.file.size) }}</span>
            </div>
            <span v-if="!item.valid" class="pending-error">{{ item.error }}</span>
            <el-button
              text
              size="small"
              :icon="Close"
              aria-label="移除"
              @click="handleRemoveFile(index)"
            />
          </div>
        </div>
      </div>

      <!-- 超限警告 -->
      <el-alert
        v-if="wouldExceedLimit"
        type="warning"
        :closable="false"
        show-icon
        class="limit-alert"
      >
        当前已有 {{ currentDocCount }} 个文档，上传后将超过上限
        {{ MAX_DOCUMENTS }}，请先删除旧文档。
      </el-alert>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div v-if="hasResult">
        <el-button @click="handleContinue">继续上传</el-button>
        <el-button type="primary" @click="handleClose">完成</el-button>
      </div>
      <div v-else-if="isUploading">
        <el-button disabled>上传中...</el-button>
      </div>
      <div v-else>
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :disabled="validFiles.length === 0 || wouldExceedLimit"
          @click="handleUpload"
        >
          开始上传（{{ validFiles.length }}）
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.upload-tip {
  font-size: $font-size-small;
  color: $color-text-placeholder;
  text-align: center;
  padding: $spacing-xs 0;
}

.pending-list {
  margin-top: $spacing-base;
  border: $layout-border;
  border-radius: $radius-base;
  overflow: hidden;
}

.pending-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm $spacing-md;
  background-color: $color-bg-card;
  font-size: $font-size-small;
  color: $color-text-regular;

  .invalid-count {
    color: $color-danger;
  }
}

.pending-items {
  max-height: 200px;
  overflow-y: auto;
}

.pending-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-top: 1px solid $color-border;

  &.invalid {
    background-color: #fef0f0;
  }
}

.pending-item-info {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.pending-name {
  font-size: $font-size-base;
  color: $color-text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pending-size {
  flex-shrink: 0;
  font-size: $font-size-small;
  color: $color-text-placeholder;
}

.pending-error {
  flex-shrink: 0;
  font-size: $font-size-small;
  color: $color-danger;
}

.limit-alert {
  margin-top: $spacing-base;
}

// 上传进度
.upload-progress {
  padding: $spacing-xl $spacing-base;
  text-align: center;

  .progress-text {
    margin-top: $spacing-base;
    font-size: $font-size-base;
    color: $color-text-regular;
  }
}

// 上传结果
.upload-result {
  .result-summary {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-base 0;
    font-size: $font-size-medium;
  }

  .result-icon {
    font-size: 24px;

    &.success {
      color: $color-success;
    }

    &.warning {
      color: $color-warning;
    }
  }

  .result-text {
    color: $color-text-primary;
  }
}

.failed-list {
  margin-top: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  background-color: #fef0f0;
  border-radius: $radius-base;

  .failed-title {
    font-size: $font-size-small;
    color: $color-text-regular;
    margin-bottom: $spacing-xs;
  }
}

.failed-item {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs 0;
  font-size: $font-size-small;

  .failed-icon {
    flex-shrink: 0;
    color: $color-danger;
  }

  .failed-name {
    flex-shrink: 0;
    max-width: 180px;
    color: $color-text-primary;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .failed-error {
    color: $color-danger;
  }
}
</style>
