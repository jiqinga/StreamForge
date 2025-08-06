<template>
  <div class="enhanced-log-filter">
    <n-card size="small" :bordered="false" class="filter-card">
      <div class="filter-content">
        <!-- 基础过滤器 -->
        <div class="filter-row">
          <div class="filter-group">
            <label class="filter-label">搜索内容</label>
            <n-input
              v-model:value="localFilters.search"
              placeholder="搜索日志内容..."
              clearable
              class="filter-input"
              @keyup.enter="handleSearch"
            >
              <template #prefix>
                <n-icon><Icon icon="mdi:magnify" /></n-icon>
              </template>
            </n-input>
          </div>

          <div class="filter-group">
            <label class="filter-label">日志级别</label>
            <n-select
              v-model:value="localFilters.level"
              placeholder="选择级别"
              clearable
              class="filter-select"
              :options="levelOptions"
            />
          </div>

          <div class="filter-group">
            <label class="filter-label">日志类型</label>
            <n-select
              v-model:value="localFilters.logType"
              placeholder="选择类型"
              clearable
              class="filter-select"
              :options="typeOptions"
            />
          </div>
        </div>

        <!-- 高级过滤器 -->
        <div class="filter-row" v-show="showAdvanced">
          <div class="filter-group">
            <label class="filter-label">时间范围</label>
            <n-date-picker
              v-model:value="localFilters.timeRange"
              type="datetimerange"
              clearable
              class="filter-date"
              :shortcuts="timeShortcuts"
            />
          </div>

          <div class="filter-group">
            <label class="filter-label">正则表达式</label>
            <n-input
              v-model:value="localFilters.regex"
              placeholder="输入正则表达式..."
              clearable
              class="filter-input"
            >
              <template #prefix>
                <n-icon><Icon icon="mdi:regex" /></n-icon>
              </template>
            </n-input>
          </div>

          <div class="filter-group">
            <label class="filter-label">排除关键词</label>
            <n-input
              v-model:value="localFilters.exclude"
              placeholder="排除包含这些词的日志..."
              clearable
              class="filter-input"
            >
              <template #prefix>
                <n-icon><Icon icon="mdi:minus-circle" /></n-icon>
              </template>
            </n-input>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="filter-actions">
          <div class="action-left">
            <n-button
              text
              type="primary"
              @click="showAdvanced = !showAdvanced"
            >
              <template #icon>
                <n-icon>
                  <Icon :icon="showAdvanced ? 'mdi:chevron-up' : 'mdi:chevron-down'" />
                </n-icon>
              </template>
              {{ showAdvanced ? '收起' : '展开' }}高级过滤
            </n-button>
          </div>

          <div class="action-right">
            <n-button @click="handleReset">
              <template #icon>
                <n-icon><Icon icon="mdi:refresh" /></n-icon>
              </template>
              重置
            </n-button>

            <n-button type="primary" @click="handleSearch">
              <template #icon>
                <n-icon><Icon icon="mdi:magnify" /></n-icon>
              </template>
              搜索
            </n-button>

            <n-button @click="handleExport" :loading="exporting">
              <template #icon>
                <n-icon><Icon icon="mdi:download" /></n-icon>
              </template>
              导出
            </n-button>
          </div>
        </div>

        <!-- 快速过滤标签 -->
        <div class="quick-filters" v-if="quickFilters.length > 0">
          <span class="quick-filter-label">快速过滤：</span>
          <n-tag
            v-for="filter in quickFilters"
            :key="filter.key"
            :type="filter.type"
            closable
            @close="removeQuickFilter(filter.key)"
            class="quick-filter-tag"
          >
            {{ filter.label }}
          </n-tag>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue';
import {
  NCard,
  NInput,
  NSelect,
  NDatePicker,
  NButton,
  NIcon,
  NTag,
  useMessage
} from 'naive-ui';
import { Icon } from '@iconify/vue';

interface LogFilters {
  search: string;
  level: string | null;
  logType: string | null;
  timeRange: [number, number] | null;
  regex: string;
  exclude: string;
}

interface QuickFilter {
  key: string;
  label: string;
  type: 'default' | 'primary' | 'info' | 'success' | 'warning' | 'error';
}

const props = defineProps({
  filters: {
    type: Object as () => LogFilters,
    default: () => ({
      search: '',
      level: null,
      logType: null,
      timeRange: null,
      regex: '',
      exclude: ''
    })
  }
});

const emit = defineEmits(['update:filters', 'search', 'reset', 'export']);

const message = useMessage();
const showAdvanced = ref(false);
const exporting = ref(false);

// 本地过滤器状态
const localFilters = reactive<LogFilters>({ ...props.filters });

// 日志级别选项
const levelOptions = [
  { label: '信息 (INFO)', value: 'INFO', type: 'info' },
  { label: '警告 (WARNING)', value: 'WARNING', type: 'warning' },
  { label: '错误 (ERROR)', value: 'ERROR', type: 'error' },
  { label: '调试 (DEBUG)', value: 'DEBUG', type: 'default' }
];

// 日志类型选项
const typeOptions = [
  { label: '任务日志', value: 'task' },
  { label: '下载日志', value: 'download' },
  { label: 'STRM生成日志', value: 'strm' }
];

// 时间快捷选项
const timeShortcuts = {
  '最近1小时': () => {
    const end = new Date();
    const start = new Date();
    start.setHours(start.getHours() - 1);
    return [start.getTime(), end.getTime()] as [number, number];
  },
  '最近6小时': () => {
    const end = new Date();
    const start = new Date();
    start.setHours(start.getHours() - 6);
    return [start.getTime(), end.getTime()] as [number, number];
  },
  '今天': () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setHours(23, 59, 59, 999);
    return [today.getTime(), end.getTime()] as [number, number];
  },
  '昨天': () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    yesterday.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setDate(end.getDate() - 1);
    end.setHours(23, 59, 59, 999);
    return [yesterday.getTime(), end.getTime()] as [number, number];
  }
};

// 快速过滤标签
const quickFilters = computed<QuickFilter[]>(() => {
  const filters: QuickFilter[] = [];

  if (localFilters.search) {
    filters.push({
      key: 'search',
      label: `搜索: ${localFilters.search}`,
      type: 'primary'
    });
  }

  if (localFilters.level) {
    const levelOption = levelOptions.find(opt => opt.value === localFilters.level);
    filters.push({
      key: 'level',
      label: `级别: ${levelOption?.label || localFilters.level}`,
      type: 'info'
    });
  }

  if (localFilters.logType) {
    const typeOption = typeOptions.find(opt => opt.value === localFilters.logType);
    filters.push({
      key: 'logType',
      label: `类型: ${typeOption?.label || localFilters.logType}`,
      type: 'success'
    });
  }

  if (localFilters.timeRange) {
    filters.push({
      key: 'timeRange',
      label: '时间范围已设置',
      type: 'warning'
    });
  }

  if (localFilters.regex) {
    filters.push({
      key: 'regex',
      label: `正则: ${localFilters.regex}`,
      type: 'error'
    });
  }

  if (localFilters.exclude) {
    filters.push({
      key: 'exclude',
      label: `排除: ${localFilters.exclude}`,
      type: 'default'
    });
  }

  return filters;
});

// 处理搜索
const handleSearch = () => {
  emit('update:filters', { ...localFilters });
  emit('search', { ...localFilters });
};

// 处理重置
const handleReset = () => {
  Object.assign(localFilters, {
    search: '',
    level: null,
    logType: null,
    timeRange: null,
    regex: '',
    exclude: ''
  });
  emit('update:filters', { ...localFilters });
  emit('reset');
};

// 处理导出
const handleExport = async () => {
  exporting.value = true;
  try {
    await emit('export', { ...localFilters });
  } finally {
    exporting.value = false;
  }
};

// 移除快速过滤标签
const removeQuickFilter = (key: string) => {
  switch (key) {
    case 'search':
      localFilters.search = '';
      break;
    case 'level':
      localFilters.level = null;
      break;
    case 'logType':
      localFilters.logType = null;
      break;
    case 'timeRange':
      localFilters.timeRange = null;
      break;
    case 'regex':
      localFilters.regex = '';
      break;
    case 'exclude':
      localFilters.exclude = '';
      break;
  }
  handleSearch();
};

// 监听外部过滤器变化
watch(() => props.filters, (newFilters) => {
  Object.assign(localFilters, newFilters);
}, { deep: true });
</script>

<style scoped>
.enhanced-log-filter {
  margin-bottom: 8px;
  flex-shrink: 0;
}

.filter-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border: 1px solid #e8e8e8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-content {
  padding: 12px;
}

.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-row:last-child {
  margin-bottom: 0;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 180px;
  flex: 1;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: #666;
  margin-bottom: 4px;
  white-space: nowrap;
}

.filter-input,
.filter-select,
.filter-date {
  min-width: 160px;
}

.filter-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  margin-top: 8px;
}

.action-left,
.action-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.quick-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.3);
  flex-wrap: wrap;
}

.quick-filter-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.quick-filter-tag {
  margin: 2px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
  }

  .filter-group {
    min-width: auto;
  }

  .filter-actions {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .action-left,
  .action-right {
    justify-content: center;
  }
}
</style>
