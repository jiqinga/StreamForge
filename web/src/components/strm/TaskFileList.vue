<template>
  <div class="toolbar-right">
    <n-input v-model:value="searchText" placeholder="搜索文件..." clearable style="width: 240px;">
      <template #prefix>
        <n-icon>
          <Icon icon="mdi:magnify" />
        </n-icon>
      </template>
    </n-input>

    <n-select v-model:value="statusFilter" placeholder="状态过滤" clearable style="width: 140px;" :options="statusOptions">
      <template #prefix>
        <n-icon>
          <Icon icon="mdi:filter-variant" />
        </n-icon>
      </template>
    </n-select>

    <n-select v-model:value="fileTypeFilter" placeholder="文件类型" clearable style="width: 160px;"
      :options="fileTypeOptions">
      <template #prefix>
        <n-icon>
          <Icon icon="mdi:file-document" />
        </n-icon>
      </template>
    </n-select>

    <n-radio-group v-model:value="viewMode" size="medium">
      <n-tooltip trigger="hover" placement="top">
        <template #trigger>
          <n-radio-button value="table">
            <n-icon>
              <Icon icon="material-symbols:table" />
            </n-icon>
          </n-radio-button>
        </template>
        表格视图
      </n-tooltip>
      <n-tooltip trigger="hover" placement="top">
        <template #trigger>
          <n-radio-button value="tree">
            <n-icon>
              <Icon icon="ph:tree-structure" />
            </n-icon>
          </n-radio-button>
        </template>
        树形视图
      </n-tooltip>
      <n-tooltip trigger="hover" placement="top">
        <template #trigger>
          <n-radio-button value="grid">
            <n-icon>
              <Icon icon="mdi:view-grid" />
            </n-icon>
          </n-radio-button>
        </template>
        网格视图
      </n-tooltip>
    </n-radio-group>

    <n-button @click="resetFilters" size="medium">
      <template #icon>
        <n-icon>
          <Icon icon="mdi:filter-off" />
        </n-icon>
      </template>
      重置过滤
    </n-button>

    <n-button @click="handleRefresh" size="medium" type="primary">
      <template #icon>
        <n-icon>
          <Icon icon="mdi:refresh" />
        </n-icon>
      </template>
      刷新数据
    </n-button>

  <!-- 文件列表内容 -->
  <div class="files-content">
      <!-- 表格视图 -->
    <div v-show="viewMode === 'table'" class="table-view">
      <div v-if="loading" class="loading-container">
        <n-spin size="large">
          <template #description>加载文件列表中...</template>
        </n-spin>
      </div>
      <div v-else-if="filteredFiles.length === 0" class="empty-container">
        <n-empty description="暂无文件数据">
          <template #icon>
            <n-icon size="48" color="#d9d9d9">
              <Icon icon="mdi:file-search-outline" />
            </n-icon>
          </template>
          <template #extra>
            <n-space>
              <n-button @click="resetFilters" v-if="searchText || statusFilter || fileTypeFilter">
                清除过滤器
              </n-button>
              <n-button @click="handleRefresh" type="primary">
                刷新数据
              </n-button>
            </n-space>
          </template>
        </n-empty>
      </div>
      <n-data-table v-else :columns="tableColumns" :data="paginatedFiles" :loading="loading"
        :pagination="paginationConfig" remote :bordered="false" :row-key="row => row.id || row.source_path" size="small"
        :row-class-name="getRowClassName" @update:page="handlePageChange" @update:page-size="handlePageSizeChange" />
    </div>

    <!-- 树形视图 -->
    <div v-show="viewMode === 'tree'" class="tree-view">
      <TaskFileTreeView :files="filteredFiles" :loading="loading" :task-id="taskId" :use-lazy-load="useLazyLoad"
        @file-click="handleFileClick" />
    </div>

    <!-- 网格视图 -->
    <div v-show="viewMode === 'grid'" class="grid-view">
      <div v-if="loading" class="loading-container">
        <n-spin size="large">
          <template #description>加载文件列表中...</template>
        </n-spin>
      </div>
      <div v-else-if="filteredFiles.length === 0" class="empty-container">
        <n-empty description="暂无文件数据">
          <template #icon>
            <n-icon size="48" color="#d9d9d9">
              <Icon icon="mdi:file-search-outline" />
            </n-icon>
          </template>
          <template #extra>
            <n-space>
              <n-button @click="resetFilters" v-if="searchText || statusFilter || fileTypeFilter">
                清除过滤器
              </n-button>
              <n-button @click="handleRefresh" type="primary">
                刷新数据
              </n-button>
            </n-space>
          </template>
        </n-empty>
      </div>
      <div v-else>
        <div class="file-grid">
          <div v-for="file in paginatedFiles" :key="file.id || file.source_path" class="file-card"
            :class="getFileCardClass(file)" @click="handleFileClick(file)">
            <div class="file-icon">
              <n-icon size="32" :color="getFileIconColor(file)">
                <Icon :icon="getFileIcon(file)" />
              </n-icon>
            </div>
            <div class="file-info">
              <div class="file-name" :title="getFileName(file.source_path)">
                {{ getFileName(file.source_path) }}
              </div>
              <div class="file-path" :title="file.source_path">
                {{ file.source_path }}
              </div>
              <div class="file-status">
                <n-tag size="small" :type="getFileStatusType(file)">
                  {{ getFileStatusText(file) }}
                </n-tag>
              </div>
              <div class="file-actions" @click.stop>
                <n-space size="small">
                  <n-button v-if="file.status === 'completed'" size="small" type="success" @click="handlePreviewClick(file)">
                    预览
                  </n-button>
                </n-space>
              </div>
            </div>
          </div>
        </div>
        <!-- 网格视图分页控件 -->
        <div class="grid-pagination">
          <n-pagination v-bind="paginationConfig" @update:page="handlePageChange"
            @update:page-size="handlePageSizeChange" />
        </div>
      </div>
    </div>
  </div>

  <!-- 文件详情对话框 -->
  <n-modal v-model:show="showFileDetail" preset="card" style="width: 1200px; height: 85vh;" :bordered="false">
    <template #header>
      <div class="enhanced-file-detail-header">
        <div class="header-left">
          <div class="file-icon-large">
            <n-icon size="28" :color="getFileIconColor(selectedFile)">
              <Icon :icon="getFileIcon(selectedFile)" />
            </n-icon>
          </div>
          <div class="header-info">
            <h3 class="file-title">{{ getFileName(selectedFile?.source_path) }}</h3>
            <div class="file-subtitle">
              <n-tag size="small" :type="getFileStatusType(selectedFile)">
                {{ getFileStatusText(selectedFile) }}
              </n-tag>
              <span class="file-type-badge">{{ getFileTypeDisplay(selectedFile?.source_path) }}</span>
            </div>
          </div>
        </div>
        <div class="header-actions">
          <n-button-group>
            <n-button :type="!showPreview ? 'primary' : 'default'" @click="showPreview = false">
              <template #icon>
                <n-icon>
                  <Icon icon="mdi:information-variant" />
                </n-icon>
              </template>
              详细信息
            </n-button>
            <n-button v-if="selectedFile?.status === 'completed'" :type="showPreview ? 'primary' : 'default'"
              @click="showPreview = true">
              <template #icon>
                <n-icon>
                  <Icon icon="mdi:eye" />
                </n-icon>
              </template>
              文件预览
            </n-button>
          </n-button-group>
        </div>
      </div>
    </template>

    <div v-if="selectedFile" class="enhanced-file-detail">
      <!-- 预览模式：只显示文件预览 -->
      <div v-if="showPreview" class="file-preview-content">
        <FilePreview v-if="selectedFile && taskId" :task-id="taskId" :file-path="selectedFile.source_path" />
      </div>

      <!-- 详情模式：显示基本信息 -->
      <div v-else class="file-info-enhanced">
        <!-- 基本信息卡片 -->
        <div class="info-cards-grid">
          <!-- 文件路径信息卡片 -->
          <div class="info-card">
            <div class="card-header">
              <n-icon size="20" color="#1890ff">
                <Icon icon="mdi:folder-outline" />
              </n-icon>
              <span class="card-title">文件路径</span>
            </div>
            <div class="card-content">
              <div class="path-item">
                <label class="path-label">源文件路径</label>
                <div class="path-value">
                  <n-text copyable class="path-text">{{ selectedFile.source_path }}</n-text>
                </div>
              </div>
              <div class="path-item" v-if="selectedFile.target_path">
                <label class="path-label">目标文件路径</label>
                <div class="path-value">
                  <n-text copyable class="path-text">{{ selectedFile.target_path }}</n-text>
                </div>
              </div>
            </div>
          </div>

          <!-- 文件属性信息卡片 -->
          <div class="info-card">
            <div class="card-header">
              <n-icon size="20" color="#52c41a">
                <Icon icon="mdi:file-document-outline" />
              </n-icon>
              <span class="card-title">文件属性</span>
            </div>
            <div class="card-content">
              <div class="attribute-grid">
                <div class="attribute-item">
                  <span class="attribute-label">文件大小</span>
                  <span class="attribute-value">{{ formatFileSize(selectedFile.file_size) }}</span>
                </div>
                <div class="attribute-item">
                  <span class="attribute-label">文件类型</span>
                  <span class="attribute-value">{{ getFileTypeDisplay(selectedFile.source_path) }}</span>
                </div>
                <div class="attribute-item">
                  <span class="attribute-label">处理时间</span>
                  <span class="attribute-value">{{ formatProcessTime(selectedFile.process_time) }}</span>
                </div>
                <div class="attribute-item">
                  <span class="attribute-label">创建时间</span>
                  <span class="attribute-value">{{ formatDate(selectedFile.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 错误信息卡片 -->
        <div v-if="shouldShowErrorCard(selectedFile)" class="error-card">
          <div class="card-header error-header">
            <n-icon size="20" color="#ff4d4f">
              <Icon icon="mdi:alert-circle" />
            </n-icon>
            <span class="card-title">{{ getErrorCardTitle(selectedFile) }}</span>
          </div>
          <div class="card-content">
            <div class="error-content">
              <n-text type="error" class="error-text">{{ getErrorMessage(selectedFile) }}</n-text>
            </div>
          </div>
        </div>
      </div>
    </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref, watch, watchEffect } from 'vue';
import type { DataTableColumns } from 'naive-ui';
import {
  NButton,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NEmpty,
  NIcon,
  NInput,
  NModal,
  NPagination,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NSpin,
  NTag,
  NText,
  NTooltip
} from 'naive-ui';
import { Icon } from '@iconify/vue';
import TaskFileTreeView from './TaskFileTreeView.vue';
import FilePreview from './FilePreview.vue';

// Props
interface Props {
  files: any[];
  loading?: boolean;
  totalCount?: number;
  currentPage?: number;
  pageSize?: number;
  taskId?: number;
  useLazyLoad?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  totalCount: 0,
  currentPage: 1,
  pageSize: 10, // 表格视图默认10条
  useLazyLoad: false
});



// Emits
const emit = defineEmits<{
  fileClick: [file: any];
  refresh: [];
  pageChange: [page: number];
  pageSizeChange: [pageSize: number];
  filterChange: [filters: { fileType?: string; search?: string; status?: string }];
}>();

// 响应式数据
const searchText = ref('');
const statusFilter = ref<string | null>(null);
const fileTypeFilter = ref<string | null>(null);
const viewMode = ref<'table' | 'tree' | 'grid'>('table');
const showFileDetail = ref(false);
const selectedFile = ref<any>(null);
const showPreview = ref(true);



// 分页状态（使用 props 中的值）
const currentPage = computed(() => props.currentPage);
const pageSize = computed(() => props.pageSize);

// 状态选项
const statusOptions = [
  { label: '✅ 成功', value: 'completed', type: 'success' as const },
  { label: '❌ 失败', value: 'failed', type: 'error' as const },
  { label: '🚫 已取消', value: 'canceled', type: 'warning' as const },
  { label: '⏳ 处理中', value: 'downloading', type: 'info' as const },
  { label: '⏸️ 等待中', value: 'pending', type: 'default' as const }
];

// 文件类型选项 - 根据系统设置分类
const fileTypeOptions = computed(() => {
  const options = [
    { label: '📹 视频文件', value: 'video' },
    { label: '🎵 音频文件', value: 'audio' },
    { label: '🖼️ 图片文件', value: 'image' },
    { label: '📝 字幕文件', value: 'subtitle' },
    { label: '📄 元数据文件', value: 'metadata' }
  ];

  return options;
});

// 文件统计
const fileStats = computed(() => {
  const stats = {
    total: props.files.length,
    success: 0,
    failed: 0,
    canceled: 0,
    processing: 0,
    pending: 0
  };

  props.files.forEach(file => {
    const status = file.status || 'unknown';
    switch (status) {
      case 'completed':
        stats.success++;
        break;
      case 'failed':
        stats.failed++;
        break;
      case 'canceled':
        stats.canceled++;
        break;
      case 'downloading':
        stats.processing++;
        break;
      case 'pending':
        stats.pending++;
        break;
    }
  });

  return stats;
});

// 直接使用props中的文件列表（后端已过滤）
const filteredFiles = computed(() => {
  return props.files;
});

// 动态分页配置，根据视图模式选择不同的分页选项
const paginationConfig = computed(() => {
  const isGridView = viewMode.value === 'grid';
  return {
    page: currentPage.value,
    pageSize: pageSize.value,
    itemCount: props.totalCount,
    showSizePicker: true,
    pageSizes: isGridView ? [12, 24, 48, 96] : [10, 20, 50, 100],
    showQuickJumper: true,
    prefix: (info: any) => `共 ${info.itemCount || 0} 条`
  };
});

// 对于后端分页，直接使用过滤后的文件数据（后端已经返回了当前页的数据）
const paginatedFiles = computed(() => {
  return filteredFiles.value;
});

// 表格列定义
const tableColumns: DataTableColumns<any> = [
  {
    title: '文件名',
    key: 'source_path',
    width: 200,
    ellipsis: {
      tooltip: true
    },
    render(row) {
      return getFileName(row.source_path);
    }
  },
  {
    title: '源文件路径',
    key: 'source_path',
    ellipsis: {
      tooltip: true
    },
    render(row) {
      return row.source_path || '-';
    }
  },
  {
    title: '目标文件路径',
    key: 'target_path',
    ellipsis: {
      tooltip: true
    },
    render(row) {
      return row.target_path || '-';
    }
  },
  {
    title: '文件大小',
    key: 'file_size',
    width: 100,
    render(row) {
      return formatFileSize(row.file_size);
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    align: 'center',
    render(row) {
      return h(
        NTag,
        {
          type: getFileStatusType(row),
          size: 'small'
        },
        {
          default: () => getFileStatusText(row)
        }
      );
    }
  },
  {
    title: '处理时间',
    key: 'process_time',
    width: 100,
    render(row) {
      return formatProcessTime(row.process_time);
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    align: 'center',
    render(row) {
      return h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                type: 'primary',
                onClick: () => handleFileClick(row)
              },
              { default: () => '详情' }
            ),
            row.status === 'completed' && h(
              NButton,
              {
                size: 'small',
                type: 'success',
                onClick: () => handlePreviewClick(row)
              },
              { default: () => '预览' }
            ),
            row.target_path && h(
              NButton,
              {
                size: 'small',
                type: 'info',
                onClick: () => copyPath(row.target_path)
              },
              { default: () => '复制' }
            )
          ]
        }
      );
    }
  }
];

// 工具函数
const getFileName = (path: string): string => {
  if (!path) return '-';
  return path.split('/').pop() || path.split('\\').pop() || path;
};

const getFileExtension = (path: string): string => {
  if (!path) return '';
  const fileName = getFileName(path);
  const lastDot = fileName.lastIndexOf('.');
  return lastDot > 0 ? fileName.substring(lastDot + 1).toLowerCase() : '';
};

// 根据文件路径获取系统设置中的文件类型显示
const getFileTypeDisplay = (path: string): string => {
  if (!path) return '未知';

  const ext = getFileExtension(path);
  if (!ext) return '未知';

  // 根据系统设置中的文件类型配置判断文件类型
  // 视频文件类型
  const videoExtensions = ['mp4', 'mkv', 'avi', 'rmvb', 'wmv', 'mov', 'm2ts', 'ts', 'iso', 'flv', 'mpg', 'mpeg', 'm4v', 'webm'];
  if (videoExtensions.includes(ext)) {
    return '📹 视频文件';
  }

  // 音频文件类型
  const audioExtensions = ['mp3', 'flac', 'wav', 'aac', 'ogg', 'm4a', 'wma', 'ape'];
  if (audioExtensions.includes(ext)) {
    return '🎵 音频文件';
  }

  // 图片文件类型
  const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'tif'];
  if (imageExtensions.includes(ext)) {
    return '🖼️ 图片文件';
  }

  // 字幕文件类型
  const subtitleExtensions = ['srt', 'ass', 'ssa', 'vtt', 'sub', 'idx'];
  if (subtitleExtensions.includes(ext)) {
    return '📝 字幕文件';
  }

  // 元数据文件类型
  const metadataExtensions = ['nfo', 'xml', 'json', 'txt'];
  if (metadataExtensions.includes(ext)) {
    return '📄 元数据文件';
  }

  // 其他文件类型
  return '📄 其他文件';
};



const formatFileSize = (size: number | string): string => {
  if (!size || size === 0) return '-';
  const bytes = typeof size === 'string' ? parseInt(size) : size;
  if (isNaN(bytes)) return '-';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let index = 0;
  let value = bytes;

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index++;
  }

  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
};

const formatProcessTime = (time: number | string): string => {
  if (!time) return '-';
  const seconds = typeof time === 'string' ? parseFloat(time) : time;
  if (isNaN(seconds)) return '-';

  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  } else if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  }
};

const formatDate = (date: string | Date): string => {
  if (!date) return '-';
  try {
    const d = new Date(date);
    return d.toLocaleString('zh-CN');
  } catch {
    return '-';
  }
};

const getFileIcon = (file: any): string => {
  const ext = getFileExtension(file.source_path);
  const iconMap: Record<string, string> = {
    'mp4': 'mdi:file-video',
    'avi': 'mdi:file-video',
    'mkv': 'mdi:file-video',
    'mov': 'mdi:file-video',
    'wmv': 'mdi:file-video',
    'flv': 'mdi:file-video',
    'webm': 'mdi:file-video',
    'm4v': 'mdi:file-video',
    'mp3': 'mdi:file-music',
    'wav': 'mdi:file-music',
    'flac': 'mdi:file-music',
    'aac': 'mdi:file-music',
    'jpg': 'mdi:file-image',
    'jpeg': 'mdi:file-image',
    'png': 'mdi:file-image',
    'gif': 'mdi:file-image',
    'bmp': 'mdi:file-image',
    'webp': 'mdi:file-image',
    'txt': 'mdi:file-document',
    'pdf': 'mdi:file-pdf-box',
    'doc': 'mdi:file-word',
    'docx': 'mdi:file-word',
    'xls': 'mdi:file-excel',
    'xlsx': 'mdi:file-excel',
    'zip': 'mdi:file-archive',
    'rar': 'mdi:file-archive',
    '7z': 'mdi:file-archive'
  };

  return iconMap[ext] || 'mdi:file';
};

const getFileIconColor = (file: any): string => {
  const status = file.status || 'unknown';
  switch (status) {
    case 'completed':
      return '#52c41a';
    case 'failed':
      return '#ff4d4f';
    case 'canceled':
      return '#fa8c16';
    case 'downloading':
      return '#1890ff';
    case 'pending':
      return '#8c8c8c';
    default:
      return '#1890ff';
  }
};

// 获取文件状态类型（用于标签颜色）
const getFileStatusType = (file: any): string => {
  if (!file) return 'default';
  const status = file.status || 'unknown';
  switch (status) {
    case 'completed':
      return 'success';
    case 'failed':
      return 'error';
    case 'canceled':
      return 'warning';
    case 'downloading':
      return 'info';
    case 'pending':
      return 'default';
    default:
      return 'default';
  }
};

// 获取文件状态文本
const getFileStatusText = (file: any): string => {
  if (!file) return '未知';
  const status = file.status || 'unknown';
  switch (status) {
    case 'completed':
      return '✅ 成功';
    case 'failed':
      return '❌ 失败';
    case 'canceled':
      return '🚫 已取消';
    case 'downloading':
      return '⏳ 处理中';
    case 'pending':
      return '⏸️ 等待中';
    default:
      return '❓ 未知';
  }
};

// 判断是否应该显示错误卡片
const shouldShowErrorCard = (file: any): boolean => {
  if (!file) return false;
  const status = file.status || 'unknown';
  return status === 'failed' || status === 'canceled';
};

// 获取错误卡片标题
const getErrorCardTitle = (file: any): string => {
  if (!file) return '错误信息';
  const status = file.status || 'unknown';
  switch (status) {
    case 'failed':
      return '错误信息';
    case 'canceled':
      return '取消原因';
    default:
      return '错误信息';
  }
};

// 获取错误信息
const getErrorMessage = (file: any): string => {
  if (!file) return '未知错误';

  const status = file.status || 'unknown';
  const errorMessage = file.error_message;

  // 如果有具体的错误信息，直接返回
  if (errorMessage && errorMessage.trim()) {
    return errorMessage;
  }

  // 根据状态返回默认信息
  switch (status) {
    case 'failed':
      return '文件处理失败，但未记录具体错误信息';
    case 'canceled':
      return '任务已被取消';
    default:
      return '未知错误';
  }
};

const getRowClassName = (row: any): string => {
  const status = row.status || 'unknown';
  switch (status) {
    case 'completed':
      return 'file-row-success';
    case 'failed':
      return 'file-row-error';
    case 'canceled':
      return 'file-row-canceled';
    case 'downloading':
      return 'file-row-processing';
    case 'pending':
      return 'file-row-pending';
    default:
      return 'file-row-unknown';
  }
};

const getFileCardClass = (file: any): string => {
  const baseClass = 'file-card';
  const status = file.status || 'unknown';
  switch (status) {
    case 'completed':
      return `${baseClass} success`;
    case 'failed':
      return `${baseClass} error`;
    case 'canceled':
      return `${baseClass} canceled`;
    case 'downloading':
      return `${baseClass} processing`;
    case 'pending':
      return `${baseClass} pending`;
    default:
      return `${baseClass} unknown`;
  }
};

// 事件处理
const handleFileClick = (file: any) => {
  selectedFile.value = file;
  showFileDetail.value = true;
  showPreview.value = false; // 默认显示基本信息
  emit('fileClick', file);
};

const handlePreviewClick = (file: any) => {
  // 只有成功的文件才能预览
  if (file.status !== 'completed') {
    return;
  }
  selectedFile.value = file;
  showFileDetail.value = true;
  showPreview.value = true; // 直接显示预览
  emit('fileClick', file);
};

const copyPath = async (path: string) => {
  try {
    await navigator.clipboard.writeText(path);
    // 这里可以添加成功提示
  } catch (error) {
    console.error('复制失败:', error);
  }
};

const resetFilters = () => {
  searchText.value = '';
  statusFilter.value = null;
  fileTypeFilter.value = null;
  // 通知父组件过滤条件已重置
  emit('filterChange', {});
};

const handleRefresh = () => {
  console.log('手动刷新文件列表');
  emit('refresh');
};

// 分页事件处理
const handlePageChange = (page: number) => {
  emit('pageChange', page);
};

const handlePageSizeChange = (newPageSize: number) => {
  emit('pageSizeChange', newPageSize);
};

// 监听过滤条件变化，通知父组件
watch([searchText, statusFilter, fileTypeFilter], () => {
  const filters: { fileType?: string; search?: string; status?: string } = {};

  if (searchText.value) {
    filters.search = searchText.value;
  }
  if (statusFilter.value !== null) {
    filters.status = statusFilter.value;
  }
  if (fileTypeFilter.value) {
    filters.fileType = fileTypeFilter.value;
  }

  emit('filterChange', filters);
  emit('pageChange', 1); // 重置到第一页
});

// 监听视图模式变化，自动调整分页大小
watch(viewMode, (newMode, oldMode) => {
  if (newMode !== oldMode) {
    const newPageSize = newMode === 'grid' ? 12 : 10;
    // 如果当前分页大小不符合新视图模式的默认值，则调整
    if (pageSize.value !== newPageSize) {
      emit('pageSizeChange', newPageSize);
    }
  }
});


</script>

<style scoped>
.task-file-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 工具栏样式 */
.files-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background-color: var(--n-card-color);
  border-radius: 8px;
  border: 1px solid var(--n-border-color);
}

.toolbar-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--n-text-color-1);
  margin: 0;
}

.file-stats {
  margin-top: 4px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 内容区域样式 */
.files-content {
  background-color: var(--n-card-color);
  border-radius: 8px;
  border: 1px solid var(--n-border-color);
  overflow: hidden;
}

.table-view {
  padding: 16px;
}

.tree-view {
  padding: 16px;
  min-height: 300px;
}

.grid-view {
  padding: 16px;
  min-height: 300px;
}

/* 加载和空状态样式 */
.loading-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 200px;
}

/* 网格视图样式 */
.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.grid-pagination {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--n-border-color);
  background-color: var(--n-card-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.file-card:hover {
  border-color: var(--n-primary-color);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.file-card.success {
  border-left: 4px solid #52c41a;
}

.file-card.error {
  border-left: 4px solid #ff4d4f;
}

.file-card.canceled {
  border-left: 4px solid #fa8c16;
}

.file-card.processing {
  border-left: 4px solid #1890ff;
}

.file-card.pending {
  border-left: 4px solid #8c8c8c;
}

.file-card.unknown {
  border-left: 4px solid #d9d9d9;
}

.file-icon {
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 600;
  color: var(--n-text-color-1);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  font-size: 12px;
  color: var(--n-text-color-3);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-status {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.file-actions {
  display: flex;
  justify-content: flex-start;
  margin-top: 8px;
}

/* 表格行样式 */
:deep(.file-row-success) {
  background-color: rgba(82, 196, 26, 0.05);
}

:deep(.file-row-error) {
  background-color: rgba(245, 34, 45, 0.05);
}

:deep(.file-row-canceled) {
  background-color: rgba(250, 140, 22, 0.05);
}

:deep(.file-row-processing) {
  background-color: rgba(24, 144, 255, 0.05);
}

:deep(.file-row-pending) {
  background-color: rgba(140, 140, 140, 0.05);
}

:deep(.file-row-unknown) {
  background-color: rgba(217, 217, 217, 0.05);
}

/* 文件详情样式 */
.file-detail {
  padding: 16px 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .files-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .toolbar-right {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .file-grid {
    grid-template-columns: 1fr;
  }

  .file-card {
    flex-direction: column;
    align-items: flex-start;
    text-align: left;
  }

  .file-icon {
    align-self: center;
  }
}

/* 增强的文件详情对话框样式 */
.enhanced-file-detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 8px 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon-large {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  background-color: rgba(24, 144, 255, 0.1);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--n-text-color-1);
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-type-badge {
  font-size: 12px;
  color: var(--n-text-color-3);
  background-color: var(--n-color-target);
  padding: 2px 6px;
  border-radius: 4px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.enhanced-file-detail {
  height: calc(85vh - 140px);
  overflow-y: auto;
  padding: 16px 0;
}

.file-info-enhanced {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.file-preview-content {
  height: calc(85vh - 180px);
  overflow: hidden;
}

/* 信息卡片网格布局 */
.info-cards-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

/* 信息卡片样式 */
.info-card {
  background-color: var(--n-card-color);
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.info-card:hover {
  border-color: var(--n-primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--n-divider-color);
  background-color: rgba(24, 144, 255, 0.02);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--n-text-color-1);
}

.card-content {
  padding: 16px 20px 20px;
}

/* 路径信息样式 */
.path-item {
  margin-bottom: 16px;
}

.path-item:last-child {
  margin-bottom: 0;
}

.path-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--n-text-color-2);
  margin-bottom: 6px;
}

.path-value {
  background-color: var(--n-color-target);
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  padding: 8px 12px;
}

.path-text {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  word-break: break-all;
}

/* 属性网格样式 */
.attribute-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.attribute-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.attribute-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--n-text-color-2);
}

.attribute-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color-1);
}

/* 错误信息卡片样式 */
.error-card {
  background-color: rgba(255, 77, 79, 0.03);
  border: 1px solid rgba(255, 77, 79, 0.2);
  border-radius: 12px;
  overflow: hidden;
}

.error-header {
  background-color: rgba(255, 77, 79, 0.05);
  border-bottom-color: rgba(255, 77, 79, 0.2);
}

.error-content {
  max-height: 200px;
  overflow-y: auto;
  background-color: rgba(255, 255, 255, 0.5);
  border-radius: 6px;
  padding: 12px;
  margin: 4px;
}

.error-text {
  display: block;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  word-break: break-all;
  white-space: pre-wrap;
  color: #d32f2f;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .info-cards-grid {
    grid-template-columns: 1fr;
  }

  .attribute-grid {
    grid-template-columns: 1fr;
  }

  .enhanced-file-detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .file-title {
    max-width: 100%;
  }
}
</style>
