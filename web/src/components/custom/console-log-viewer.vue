<template>
  <div class="enhanced-log-viewer">
    <!-- 日志统计面板 -->
    <div class="log-stats-panel" v-if="showStats">
      <n-card size="small" :bordered="false" class="stats-card">
        <div class="stats-grid">
          <div class="stat-item">
            <n-icon size="16" class="stat-icon info">
              <Icon icon="mdi:information" />
            </n-icon>
            <span class="stat-label">信息</span>
            <span class="stat-value">{{ logStats.info }}</span>
          </div>
          <div class="stat-item">
            <n-icon size="16" class="stat-icon warning">
              <Icon icon="mdi:alert" />
            </n-icon>
            <span class="stat-label">警告</span>
            <span class="stat-value">{{ logStats.warning }}</span>
          </div>
          <div class="stat-item">
            <n-icon size="16" class="stat-icon error">
              <Icon icon="mdi:alert-circle" />
            </n-icon>
            <span class="stat-label">错误</span>
            <span class="stat-value">{{ logStats.error }}</span>
          </div>
          <div class="stat-item">
            <n-icon size="16" class="stat-icon debug">
              <Icon icon="mdi:bug" />
            </n-icon>
            <span class="stat-label">调试</span>
            <span class="stat-value">{{ logStats.debug }}</span>
          </div>
          <div class="stat-item">
            <n-icon size="16" class="stat-icon">
              <Icon icon="mdi:format-list-numbered" />
            </n-icon>
            <span class="stat-label">总计</span>
            <span class="stat-value">{{ logStats.total }}</span>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 工具栏 -->
    <div class="log-toolbar">
      <div class="toolbar-left">
        <n-button-group size="small">
          <n-button
            :type="displayMode === 'console' ? 'primary' : 'default'"
            @click="displayMode = 'console'"
          >
            <template #icon>
              <n-icon><Icon icon="mdi:console" /></n-icon>
            </template>
            控制台
          </n-button>
          <n-button
            :type="displayMode === 'structured' ? 'primary' : 'default'"
            @click="displayMode = 'structured'"
          >
            <template #icon>
              <n-icon><Icon icon="mdi:format-list-bulleted" /></n-icon>
            </template>
            结构化
          </n-button>
        </n-button-group>

        <n-divider vertical />

        <n-button size="small" @click="showStats = !showStats">
          <template #icon>
            <n-icon><Icon icon="mdi:chart-bar" /></n-icon>
          </template>
          {{ showStats ? '隐藏' : '显示' }}统计
        </n-button>

        <n-select
          v-model:value="currentTheme"
          size="small"
          style="width: 120px"
          :options="themeOptions"
        />
      </div>

      <div class="toolbar-right">
        <!-- 实时更新和刷新按钮 -->
        <template v-if="showRealTimeControls">
          <n-button
            size="small"
            @click="emit('toggle-real-time')"
            :type="isRealTimeEnabled ? 'success' : 'default'"
            :loading="logLoading"
          >
            <template #icon>
              <n-icon>
                <Icon :icon="isRealTimeEnabled ? 'mdi:pause' : 'mdi:play'" />
              </n-icon>
            </template>
            {{ isRealTimeEnabled ? '暂停' : '开启' }}实时更新
          </n-button>

          <n-button size="small" @click="emit('refresh-logs')" :loading="logLoading">
            <template #icon>
              <n-icon>
                <Icon icon="mdi:refresh" />
              </n-icon>
            </template>
            刷新
          </n-button>
        </template>

        <n-button size="small" @click="clearLogs" type="warning">
          <template #icon>
            <n-icon><Icon icon="mdi:delete-sweep" /></n-icon>
          </template>
          清空
        </n-button>

        <n-button size="small" @click="scrollToBottom">
          <template #icon>
            <n-icon><Icon icon="mdi:arrow-down" /></n-icon>
          </template>
          到底部
        </n-button>
      </div>
    </div>

    <!-- 日志内容区域 -->
    <div class="log-content-wrapper">
      <!-- 控制台模式 -->
      <div
        v-show="displayMode === 'console'"
        ref="logContainer"
        class="log-container console-mode"
        :class="getThemeClass()"
        :style="containerStyle"
        @scroll="handleScroll"
      >
        <div class="log-content">
          <div
            v-for="(line, index) in visibleLines"
            :key="index"
            :class="getLineClass(line)"
            class="log-line"
            v-html="highlightSearchTerm(formatLine(line))"
          ></div>
        </div>
      </div>

      <!-- 结构化模式 -->
      <div
        v-show="displayMode === 'structured'"
        class="log-container structured-mode"
        :style="containerStyle"
      >
        <n-virtual-list
          :items="visibleLines as any[]"
          :item-size="60"
          :style="containerStyle"
        >
          <template #default="{ item, index }">
            <div class="structured-log-item" :class="getStructuredItemClass(item)">
              <div class="log-header">
                <n-tag
                  :type="getLogLevelTagType(item)"
                  size="small"
                  class="level-tag"
                >
                  {{ getLogLevel(item) }}
                </n-tag>
                <span class="log-timestamp">{{ getLogTimestamp(item) }}</span>
                <div class="log-actions">
                  <n-button size="tiny" text @click="copyLogLine(item)">
                    <template #icon>
                      <n-icon><Icon icon="mdi:content-copy" /></n-icon>
                    </template>
                  </n-button>
                </div>
              </div>
              <div class="log-message" v-html="highlightSearchTerm(getLogMessage(item))"></div>
            </div>
          </template>
        </n-virtual-list>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, PropType } from 'vue';
import {
  NCard,
  NIcon,
  NButton,
  NButtonGroup,
  NDivider,
  NTag,
  NVirtualList,
  useMessage
} from 'naive-ui';
import { Icon } from '@iconify/vue';

interface LogLine {
  text: string;
  level?: string;
  timestamp?: string;
}

const props = defineProps({
  logs: {
    type: Array as PropType<string[] | LogLine[]>,
    default: () => []
  },
  height: {
    type: Number,
    default: undefined
  },
  searchTerm: {
    type: String,
    default: ''
  },
  levelFilter: {
    type: String,
    default: ''
  },
  showStats: {
    type: Boolean,
    default: true
  },
  isRealTimeEnabled: {
    type: Boolean,
    default: false
  },
  logLoading: {
    type: Boolean,
    default: false
  },
  showRealTimeControls: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['clear-logs', 'toggle-real-time', 'refresh-logs']);

const message = useMessage();
const logContainer = ref<HTMLElement | null>(null);
const displayMode = ref<'console' | 'structured'>('console');
const showStats = ref(props.showStats);
const currentTheme = ref('dark');

// 计算容器样式
const containerStyle = computed(() => {
  if (props.height) {
    return { height: `${props.height}px`, minHeight: `${props.height}px` };
  }
  return { height: '100%', maxHeight: '100%', minHeight: '300px' };
});

// 主题选项
const themeOptions = [
  { label: '深色主题', value: 'dark' },
  { label: '浅色主题', value: 'light' },
  { label: '高对比度', value: 'high-contrast' },
  { label: 'VS Code', value: 'vscode' }
];

// 计算日志统计信息
const logStats = computed(() => {
  const stats = {
    total: 0,
    info: 0,
    warning: 0,
    error: 0,
    debug: 0
  };

  props.logs.forEach(line => {
    stats.total++;
    const level = getLogLevel(line).toUpperCase();

    switch (level) {
      case 'INFO':
        stats.info++;
        break;
      case 'WARNING':
        stats.warning++;
        break;
      case 'ERROR':
        stats.error++;
        break;
      case 'DEBUG':
        stats.debug++;
        break;
    }
  });

  return stats;
});

// 计算可见行 - 现在显示所有日志，只过滤不分页
const visibleLines = computed(() => {
  return props.logs.filter((line) => {
    // 如果是字符串类型
    if (typeof line === 'string') {
      // 级别过滤
      if (props.levelFilter && !line.includes(`[${props.levelFilter.toUpperCase()}]`)) {
        return false;
      }
      // 搜索词过滤
      if (props.searchTerm && !line.toLowerCase().includes(props.searchTerm.toLowerCase())) {
        return false;
      }
      return true;
    }
    // 如果是对象类型
    else {
      // 级别过滤
      if (props.levelFilter && line.level !== props.levelFilter.toUpperCase()) {
        return false;
      }
      // 搜索词过滤
      if (props.searchTerm && !line.text.toLowerCase().includes(props.searchTerm.toLowerCase())) {
        return false;
      }
      return true;
    }
  });
});

// 获取日志级别
const getLogLevel = (line: string | LogLine): string => {
  if (typeof line === 'string') {
    const levelMatch = line.match(/\[(INFO|ERROR|WARNING|DEBUG)\]/i);
    return levelMatch ? levelMatch[1].toUpperCase() : 'INFO';
  } else {
    return line.level?.toUpperCase() || 'INFO';
  }
};

// 获取日志时间戳
const getLogTimestamp = (line: string | LogLine): string => {
  if (typeof line === 'string') {
    const timestampMatch = line.match(/\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/);
    return timestampMatch ? timestampMatch[1] : new Date().toLocaleString();
  } else {
    return line.timestamp || new Date().toLocaleString();
  }
};

// 获取日志消息内容
const getLogMessage = (line: string | LogLine): string => {
  if (typeof line === 'string') {
    // 移除时间戳和级别标签，只保留消息内容
    return line.replace(/^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]\s*\[(INFO|ERROR|WARNING|DEBUG)\]\s*/, '');
  } else {
    return line.text;
  }
};

// 检测日志行级别并返回对应的CSS类
const getLineClass = (line: string | LogLine) => {
  const level = getLogLevel(line);
  const classes = ['log-line'];

  switch (level) {
    case 'ERROR':
      classes.push('log-error');
      break;
    case 'WARNING':
      classes.push('log-warning');
      break;
    case 'INFO':
      classes.push('log-info');
      break;
    case 'DEBUG':
      classes.push('log-debug');
      break;
  }

  return classes.join(' ');
};

// 获取结构化日志项的CSS类
const getStructuredItemClass = (line: string | LogLine) => {
  const level = getLogLevel(line);
  return `structured-item-${level.toLowerCase()}`;
};

// 获取日志级别标签类型
const getLogLevelTagType = (line: string | LogLine): 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error' => {
  const level = getLogLevel(line);

  switch (level) {
    case 'ERROR':
      return 'error';
    case 'WARNING':
      return 'warning';
    case 'INFO':
      return 'info';
    case 'DEBUG':
      return 'default';
    default:
      return 'default';
  }
};

// 格式化日志行
const formatLine = (line: string | LogLine): string => {
  if (typeof line === 'string') {
    return line;
  } else {
    return line.text;
  }
};

// 高亮搜索词
const highlightSearchTerm = (text: string): string => {
  if (!props.searchTerm) return text;

  const regex = new RegExp(`(${escapeRegExp(props.searchTerm)})`, 'gi');
  return text.replace(regex, '<span class="highlight">$1</span>');
};

// 转义正则表达式特殊字符
const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
};

// 复制日志行
const copyLogLine = async (line: string | LogLine) => {
  try {
    const text = formatLine(line);
    await navigator.clipboard.writeText(text);
    message.success('日志已复制到剪贴板');
  } catch (error) {
    message.error('复制失败');
  }
};

// 清空日志
const clearLogs = () => {
  emit('clear-logs');
};

// 获取主题类名
const getThemeClass = () => {
  return `theme-${currentTheme.value}`;
};

// 处理滚动事件（简化版本，仅用于其他可能的滚动处理）
const handleScroll = () => {
  // 可以在这里添加其他滚动相关的逻辑
};

// 滚动到底部
const scrollToBottom = () => {
  if (!logContainer.value) return;

  nextTick(() => {
    if (!logContainer.value) return;
    logContainer.value.scrollTop = logContainer.value.scrollHeight;
  });
};

// 监听日志变化，有新日志时自动滚动到底部（配合实时更新功能）
watch(() => props.logs.length, (newVal, oldVal) => {
  if (newVal > oldVal) {
    scrollToBottom();
  }
});

// 监听过滤器变化，重置滚动位置
watch([() => props.searchTerm, () => props.levelFilter], () => {
  scrollToBottom();
});

// 组件挂载完成后滚动到底部
onMounted(() => {
  scrollToBottom();
});
</script>

<style scoped>
.enhanced-log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', Courier, monospace;
  font-size: 14px;
  line-height: 1.5;
  background: #f8f9fa;
  border-radius: 8px;
  overflow: hidden;
}

/* 统计面板样式 */
.log-stats-panel {
  padding: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stats-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  transition: all 0.3s ease;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.stat-icon {
  margin-bottom: 4px;
}

.stat-icon.info {
  color: #3794ff;
}

.stat-icon.warning {
  color: #faad14;
}

.stat-icon.error {
  color: #ff4d4f;
}

.stat-icon.debug {
  color: #b267e6;
}

.stat-label {
  font-size: 12px;
  opacity: 0.9;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
}

/* 工具栏样式 */
.log-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-bottom: 1px solid #e8e8e8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 日志内容区域 */
.log-content-wrapper {
  flex: 1;
  overflow: hidden;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

/* 日志容器基础样式 */
.log-container {
  flex: 1;
  min-height: 400px;
  height: 100%;
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
  border-radius: 4px;
  border: 1px solid #e8e8e8;
}

/* 控制台模式样式 */
.console-mode {
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  transition: all 0.3s ease;
  scrollbar-width: thin;
  scrollbar-color: #888 #f1f1f1;
  height: 100%;
  min-height: 300px;
}

.console-mode::-webkit-scrollbar {
  width: 8px;
}

.console-mode::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.console-mode::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

.console-mode::-webkit-scrollbar-thumb:hover {
  background: #555;
}

/* 结构化模式样式 */
.structured-mode {
  overflow: hidden;
}

/* 主题样式 */
.theme-dark {
  background-color: #1e1e1e;
  color: #d4d4d4;
}

.theme-light {
  background-color: #ffffff;
  color: #333333;
}

.theme-high-contrast {
  background-color: #000000;
  color: #ffffff;
}

.theme-vscode {
  background-color: #1e1e1e;
  color: #cccccc;
  font-family: 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
}

.log-content {
  font-family: 'Consolas', 'Monaco', 'Courier New', Courier, monospace;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  box-sizing: border-box;
  padding: 0;
  margin: 0;
}

.log-line {
  display: block;
  white-space: pre-wrap;
  word-break: break-word;
  word-wrap: break-word;
  overflow-wrap: break-word;
  hyphens: auto;
  padding: 2px 8px 2px 12px;
  border-left: 3px solid transparent;
  margin: 1px 0;
  transition: all 0.2s ease;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
  text-overflow: ellipsis;
}

.log-line:hover {
  background-color: rgba(255, 255, 255, 0.05);
  border-left-color: #666;
}

/* 特殊处理长URL和路径的换行 */
.log-line {
  /* 确保URL和路径能够在合适的位置换行 */
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* 针对包含URL的日志行进行特殊处理 */
.log-line:has-text("http"),
.log-line:has-text("https"),
.log-line:has-text("ftp") {
  word-break: break-all;
}

/* 确保所有文本内容都不会溢出 */
.log-line * {
  max-width: 100%;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* 处理代码和路径 */
.log-line code,
.log-line pre {
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

/* 深色主题日志级别颜色 */
.theme-dark .log-error {
  color: #ff6b6b;
  border-left-color: #ff6b6b;
}

.theme-dark .log-warning {
  color: #feca57;
  border-left-color: #feca57;
}

.theme-dark .log-info {
  color: #54a0ff;
  border-left-color: #54a0ff;
}

.theme-dark .log-debug {
  color: #a55eea;
  border-left-color: #a55eea;
}

/* 浅色主题日志级别颜色 */
.theme-light .log-error {
  color: #d32f2f;
  border-left-color: #d32f2f;
}

.theme-light .log-warning {
  color: #f57c00;
  border-left-color: #f57c00;
}

.theme-light .log-info {
  color: #1976d2;
  border-left-color: #1976d2;
}

.theme-light .log-debug {
  color: #7b1fa2;
  border-left-color: #7b1fa2;
}

.theme-light .log-line:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

/* 高对比度主题日志级别颜色 */
.theme-high-contrast .log-error {
  color: #ff0000;
  border-left-color: #ff0000;
  font-weight: bold;
}

.theme-high-contrast .log-warning {
  color: #ffff00;
  border-left-color: #ffff00;
  font-weight: bold;
}

.theme-high-contrast .log-info {
  color: #00ffff;
  border-left-color: #00ffff;
}

.theme-high-contrast .log-debug {
  color: #ff00ff;
  border-left-color: #ff00ff;
}

/* VS Code主题日志级别颜色 */
.theme-vscode .log-error {
  color: #f44747;
  border-left-color: #f44747;
}

.theme-vscode .log-warning {
  color: #ffcc02;
  border-left-color: #ffcc02;
}

.theme-vscode .log-info {
  color: #3794ff;
  border-left-color: #3794ff;
}

.theme-vscode .log-debug {
  color: #b267e6;
  border-left-color: #b267e6;
}

/* 结构化模式额外样式 */
.structured-mode {
  background: white;
  padding: 0;
}

.structured-log-item {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s ease;
}

.structured-log-item:hover {
  background-color: #f8f9fa;
}

.structured-item-error {
  border-left: 4px solid #ff4d4f;
  background-color: #fff2f0;
}

.structured-item-warning {
  border-left: 4px solid #faad14;
  background-color: #fffbe6;
}

.structured-item-info {
  border-left: 4px solid #1890ff;
  background-color: #f6ffed;
}

.structured-item-debug {
  border-left: 4px solid #722ed1;
  background-color: #f9f0ff;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.level-tag {
  font-weight: bold;
}

.log-timestamp {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

.log-actions {
  margin-left: auto;
}

.log-message {
  font-family: 'Consolas', 'Monaco', 'Courier New', Courier, monospace;
  font-size: 13px;
  line-height: 1.4;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

/* 高亮样式 */
.highlight {
  background-color: #fff566;
  color: #333;
  font-weight: bold;
  border-radius: 2px;
  padding: 1px 2px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .log-toolbar {
    flex-direction: column;
    gap: 8px;
    align-items: stretch;
  }

  .toolbar-left,
  .toolbar-right {
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
