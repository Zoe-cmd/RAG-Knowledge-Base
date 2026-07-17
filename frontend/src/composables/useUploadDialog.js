/**
 * 上传弹窗共享状态。
 *
 * 模块级 ref 保证全局唯一实例：AppSidebar 持有弹窗，
 * 对话区空状态、文档列表空状态等均可通过 open() 触发。
 * 避免为单一布尔值引入完整 Pinia store。
 */
import { ref } from 'vue';

/** 弹窗可见性（模块级单例） */
const visible = ref(false);

/** 打开上传弹窗 */
function open() {
  visible.value = true;
}

/** 关闭上传弹窗 */
function close() {
  visible.value = false;
}

/**
 * 上传弹窗组合式函数。
 *
 * @returns {{ visible: import('vue').Ref<boolean>, open: Function, close: Function }}
 */
export function useUploadDialog() {
  return { visible, open, close };
}
