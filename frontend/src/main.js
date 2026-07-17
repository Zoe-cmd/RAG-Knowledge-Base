/**
 * 应用入口。
 *
 * 初始化 Vue 应用，注册 Element Plus、Pinia、路由。
 * 采用按需引入 Element Plus 样式（全量样式）+ 中文语言包。
 */
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import 'element-plus/dist/index.css';

import App from './App.vue';
import router from './router';
import './styles/global.scss';

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn });

app.mount('#app');
