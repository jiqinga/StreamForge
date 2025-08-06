<template>
  <div>
    <n-card :bordered="false" class="h-full rounded-8px shadow-sm">
      <div class="flex flex-col space-y-4 mb-4">
        <div class="flex justify-between">
          <h2 class="text-xl font-bold">STRM处理任务管理</h2>
          <n-space>
            <n-button type="primary" @click="goToGenerate">新建STRM任务</n-button>
          </n-space>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <n-input v-model:value="searchValue" placeholder="搜索任务名称..." clearable style="width: 200px"
            @keyup.enter="handleSearch" />

          <n-date-picker v-model:value="dateRange" type="daterange" clearable style="width: 260px" placeholder="选择时间范围"
            :shortcuts="dateShortcuts" />

          <n-select v-model:value="statusFilter" placeholder="任务状态" clearable style="width: 150px"
            :options="statusOptions" />

          <n-button type="primary" size="medium" style="width: 80px; height: 34px;" @click="handleSearch">
            搜索
          </n-button>

          <n-button size="medium" style="height: 34px;" @click="clearFilters">
            清除筛选
          </n-button>

          <!-- 自动刷新控制 -->
          <div class="auto-refresh-control">
            <n-tooltip trigger="hover" placement="top">
              <template #trigger>
                <n-switch
                  v-model:value="autoRefreshEnabled"
                  @update:value="toggleAutoRefresh"
                  size="medium"
                >
                  <template #checked>
                    <n-icon size="16">
                      <Icon icon="mdi:refresh" />
                    </n-icon>
                  </template>
                  <template #unchecked>
                    <n-icon size="16">
                      <Icon icon="mdi:refresh-off" />
                    </n-icon>
                  </template>
                </n-switch>
              </template>
              <div style="max-width: 200px;">
                <div style="font-weight: 600; margin-bottom: 4px;">自动刷新功能</div>
                <div style="font-size: 12px; line-height: 1.4;">
                  开启后，按设定的间隔时间自动更新任务列表。
                </div>
              </div>
            </n-tooltip>

            <!-- 刷新间隔设置 -->
            <n-select
              v-model:value="refreshInterval"
              @update:value="updateRefreshInterval"
              size="small"
              style="width: 80px;"
              :options="refreshIntervalOptions"
            />

            <div class="refresh-status">
              <span class="refresh-label">自动刷新</span>
              <span v-if="autoRefreshEnabled" class="refresh-countdown">
                {{ refreshCountdown }}s
              </span>
              <span v-else class="refresh-disabled">
                已关闭
              </span>
            </div>
          </div>
        </div>
      </div>

      <n-data-table :columns="columns" :data="tasksData" :loading="loading" :pagination="{
        page: pagination.page,
        pageSize: pagination.pageSize,
        showSizePicker: true,
        pageSizes: [10, 20, 50, 100],
        itemCount: pagination.itemCount,
        prefix: ({ itemCount }) => `共 ${itemCount} 条`,
        showQuickJumper: true
      }" remote :row-key="row => row.id" @update:page="handlePageChange" @update:page-size="handlePageSizeChange" />
    </n-card>

    <!-- 任务详情对话框 -->
    <n-modal v-model:show="showTaskDetailModal" preset="card" :bordered="false" size="huge"
      style="max-width: 1200px; width: 95vw; margin-top: 20px">
      <template #header>
        <div class="task-detail-header">
          <div class="task-header-main">
            <div class="task-title">
              <span class="task-icon">⚙️</span>
              <span class="task-name">{{ currentTask?.name || '任务详情' }}</span>
            </div>
          </div>
        </div>
      </template>

      <div v-if="currentTask" class="task-detail-container">

        <n-tabs type="line" animated class="task-detail-tabs" @update:value="handleTabChange">
          <n-tab-pane name="overview" tab="📊 任务概览">

            <!-- 重构后的任务详细信息 -->
            <div class="task-info-section">
              <div class="section-title-wrapper">
                <h3 class="section-title">
                  <div class="title-icon-wrapper">
                    <n-icon size="20">
                      <Icon icon="mdi:information-variant" />
                    </n-icon>
                  </div>
                  <span>任务详细信息</span>
                </h3>
              </div>

              <!-- 重新平衡的信息卡片网格 -->
              <div class="enhanced-info-grid">
                <!-- 基本配置卡片 -->
                <div class="info-card primary-card">
                  <div class="card-header">
                    <div class="card-icon primary-icon">
                      <n-icon size="24">
                        <Icon icon="mdi:cog" />
                      </n-icon>
                    </div>
                    <div class="card-title">
                      <h4>基本配置</h4>
                      <span class="card-subtitle">任务基础设置信息</span>
                    </div>
                  </div>
                  <div class="card-content">
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:identifier" />
                        </n-icon>
                        任务ID
                      </div>
                      <n-tag size="small" type="info" :bordered="false">
                        🆔 ID: {{ currentTask?.id }}
                      </n-tag>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:format-title" />
                        </n-icon>
                        任务名称
                      </div>
                      <div class="info-value">{{ currentTask.name || `任务 ${currentTask.id}` }}</div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:state-machine" />
                        </n-icon>
                        任务状态
                      </div>
                      <div class="info-value">
                        <TaskStatusDisplay :status="currentTask?.status" :taskType="currentTask?.task_type" />
                      </div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:cpu-64-bit" />
                        </n-icon>
                        处理线程
                      </div>
                      <div class="info-value">{{ currentTask.threads || 1 }}</div>
                    </div>
                    <div class="info-row full-width">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:folder-outline" />
                        </n-icon>
                        输出目录
                      </div>
                      <div class="enhanced-output-dir">
                        <div class="path-display-container">
                          <div class="path-icon">
                            <n-icon size="18" color="#1890ff">
                              <Icon icon="mdi:folder-open" />
                            </n-icon>
                          </div>
                          <div class="path-content">
                            <div class="path-text" :title="currentTask.output_dir">
                              {{ currentTask.output_dir || '默认输出目录' }}
                            </div>
                            <div class="path-actions">
                              <n-button
                                size="tiny"
                                type="primary"
                                text
                                @click="copyOutputDir"
                                :disabled="!currentTask.output_dir"
                                class="copy-action"
                              >
                                <template #icon>
                                  <n-icon size="14">
                                    <Icon icon="mdi:content-copy" />
                                  </n-icon>
                                </template>
                                复制路径
                              </n-button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 执行与服务器信息卡片 -->
                <div class="info-card time-card">
                  <div class="card-header">
                    <div class="card-icon time-icon">
                      <n-icon size="24">
                        <Icon icon="mdi:server-network" />
                      </n-icon>
                    </div>
                    <div class="card-title">
                      <h4>执行与服务器信息</h4>
                      <span class="card-subtitle">任务执行时间与服务器配置</span>
                    </div>
                  </div>
                  <div class="card-content">
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:play-circle" />
                        </n-icon>
                        开始时间
                      </div>
                      <div class="info-value time-value">
                        {{ currentTask.start_time ? formatDate(currentTask.start_time) : '尚未开始' }}
                      </div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:check-circle" />
                        </n-icon>
                        完成时间
                      </div>
                      <div class="info-value time-value">
                        {{ currentTask.end_time ? formatDate(currentTask.end_time) : '尚未完成' }}
                      </div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:timer" />
                        </n-icon>
                        处理时长
                      </div>
                      <div class="info-value duration-value"
                        :class="{ 'processing-status': isTaskProcessing(currentTask) }">
                        {{ getTaskDuration(currentTask) }}
                      </div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:server" />
                        </n-icon>
                        媒体服务器
                      </div>
                      <div class="info-value server-url">{{ currentTask.server_url || '未知服务器' }}</div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:download-network" />
                        </n-icon>
                        下载服务器
                      </div>
                      <div class="info-value server-url">
                        {{ currentTask.download_server_url || currentTask.server_url || '未知服务器' }}
                        <span v-if="!currentTask.download_server_url" class="server-note">（与媒体服务器相同）</span>
                      </div>
                    </div>
                    <div class="info-row">
                      <div class="info-label">
                        <n-icon size="16">
                          <Icon icon="mdi:harddisk" />
                        </n-icon>
                        资源大小
                      </div>
                      <div class="info-value">{{ formatFileSize(currentTask.total_size || 0) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 文件统计与处理进度 -->
            <div class="progress-stats-section">
              <h3 class="section-title">
                <n-icon>
                  <Icon icon="mdi:chart-line" />
                </n-icon>
                文件统计
              </h3>

              <div class="progress-stats-grid">
                <!-- 总体进度卡片 -->
                <div class="progress-card overall">
                  <div class="progress-card-header">
                    <div class="progress-card-icon">
                      <n-icon size="24">
                        <Icon icon="mdi:chart-pie" />
                      </n-icon>
                    </div>
                    <div class="progress-card-title">
                      <h4>总体进度</h4>
                      <span class="progress-card-subtitle">{{ getTotalProcessedFiles(currentTask) }} / {{
                        currentTask.total_files
                        || 0 }} 文件</span>
                    </div>
                    <div class="progress-card-percentage">
                      {{ getTaskProgressPercentage(currentTask) }}%
                    </div>
                  </div>
                  <div class="progress-card-body">
                    <SegmentedProgressBar
                      :success-count="getTotalSuccessFiles(currentTask)"
                      :failed-count="getTotalFailedFiles(currentTask)"
                      :total="currentTask.total_files || 0"
                      :processing="currentTask.status === 'RUNNING'"
                      :height="8"
                      :border-radius="4"
                      success-color="#52c41a"
                      failed-color="#f5222d"
                      tooltip-title="总体文件处理进度"
                    />
                    <div class="progress-card-stats">
                      <div class="stat-item">
                        <span class="stat-label">成功</span>
                        <span class="stat-value success">{{ getTotalSuccessFiles(currentTask) }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">失败</span>
                        <span class="stat-value error">{{ getTotalFailedFiles(currentTask) }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- STRM文件进度卡片 -->
                <div class="progress-card strm">
                  <div class="progress-card-header">
                    <div class="progress-card-icon">
                      <n-icon size="24">
                        <Icon icon="mdi:file-video" />
                      </n-icon>
                    </div>
                    <div class="progress-card-title">
                      <h4>STRM文件</h4>
                      <span class="progress-card-subtitle">{{ (currentTask.strm_success || 0) + (currentTask.strm_failed || 0) }} / {{
                        currentTask.strm_files_count || 0 }} 文件</span>
                    </div>
                    <div class="progress-card-percentage">
                      {{ getStrmProgressPercentage(currentTask) }}%
                    </div>
                  </div>
                  <div class="progress-card-body">
                    <SegmentedProgressBar
                      :success-count="currentTask.strm_success || 0"
                      :failed-count="currentTask.strm_failed || 0"
                      :total="currentTask.strm_files_count || 0"
                      :processing="currentTask.status === 'RUNNING'"
                      :height="8"
                      :border-radius="4"
                      success-color="#52c41a"
                      failed-color="#f5222d"
                      tooltip-title="STRM文件处理进度"
                    />
                    <div class="progress-card-stats">
                      <div class="stat-item">
                        <span class="stat-label">成功</span>
                        <span class="stat-value success">{{ currentTask.strm_success || 0 }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">失败</span>
                        <span class="stat-value error">{{ currentTask.strm_failed || 0 }}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 资源文件进度卡片 -->
                <div class="progress-card resource">
                  <div class="progress-card-header">
                    <div class="progress-card-icon">
                      <n-icon size="24">
                        <Icon icon="mdi:file-download" />
                      </n-icon>
                    </div>
                    <div class="progress-card-title">
                      <h4>资源文件</h4>
                      <span class="progress-card-subtitle">{{ (currentTask.resource_success || 0) + (currentTask.resource_failed || 0) }} / {{
                        currentTask.resource_files_count || 0 }} 文件</span>
                    </div>
                    <div class="progress-card-percentage">
                      {{ getResourceProgressPercentage(currentTask) }}%
                    </div>
                  </div>
                  <div class="progress-card-body">
                    <SegmentedProgressBar
                      :success-count="currentTask.resource_success || 0"
                      :failed-count="currentTask.resource_failed || 0"
                      :total="currentTask.resource_files_count || 0"
                      :processing="currentTask.status === 'RUNNING'"
                      :height="8"
                      :border-radius="4"
                      success-color="#52c41a"
                      failed-color="#f5222d"
                      tooltip-title="资源文件处理进度"
                    />
                    <div class="progress-card-stats">
                      <div class="stat-item">
                        <span class="stat-label">成功</span>
                        <span class="stat-value success">{{ currentTask.resource_success || 0 }}</span>
                      </div>
                      <div class="stat-item">
                        <span class="stat-label">失败</span>
                        <span class="stat-value error">{{ currentTask.resource_failed || 0 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>




            <!-- 任务操作 -->
            <div class="task-actions" v-if="['SUCCESS', 'COMPLETED'].includes(currentTask.status)">
              <h3 class="section-title">
                <n-icon>
                  <Icon icon="mdi:cog-play" />
                </n-icon>
                任务操作
              </h3>
              <div class="action-buttons">
                <n-button type="primary" size="large" @click="handleDownload(currentTask.id)">
                  <template #icon>
                    <n-icon>
                      <Icon icon="mdi:download" />
                    </n-icon>
                  </template>
                  下载处理结果
                </n-button>
                <n-button size="large" @click="openLogViewer(currentTask.id)">
                  <template #icon>
                    <n-icon>
                      <Icon icon="mdi:text-box" />
                    </n-icon>
                  </template>
                  查看处理日志
                </n-button>
              </div>
            </div>

            <!-- 警告信息 -->
            <n-alert v-if="currentTask && currentTask.total_files === 0" type="warning" class="mt-4">
              <template #icon>
                <n-icon>
                  <Icon icon="mdi:alert" />
                </n-icon>
              </template>
              <template #header>未找到可处理的文件</template>
              请检查上传的文件是否包含视频文件，或检查系统设置中的文件类型配置是否正确。
            </n-alert>
          </n-tab-pane>

          <n-tab-pane name="files" tab="📁 文件列表">
            <div v-if="!filesLoaded && !fileLoading" class="file-list-placeholder">
              <n-empty description="点击刷新按钮加载文件列表">
                <template #icon>
                  <n-icon size="48" color="#d9d9d9">
                    <Icon icon="mdi:file-search-outline" />
                  </n-icon>
                </template>
                <template #extra>
                  <n-button type="primary" @click="() => fetchTaskFiles(currentTask?.id, 1, 10)">
                    <template #icon>
                      <n-icon>
                        <Icon icon="mdi:refresh" />
                      </n-icon>
                    </template>
                    加载文件列表
                  </n-button>
                </template>
              </n-empty>
            </div>
            <TaskFileList
              v-else
              :files="currentTask?.files || []"
              :loading="fileLoading"
              :total-count="fileListTotal"
              :current-page="fileListPage"
              :page-size="fileListPageSize"
              :task-id="currentTask?.id"
              :use-lazy-load="true"
              @file-click="handleFileClick"
              @refresh="() => fetchTaskFiles(currentTask?.id, fileListPage, fileListPageSize, currentFileFilters)"
              @page-change="handleFilePageChange"
              @page-size-change="handleFilePageSizeChange"
              @filter-change="handleFileFilterChange"
            />
          </n-tab-pane>
        </n-tabs>
      </div>
    </n-modal>

    <!-- 增强的任务日志对话框 -->
    <n-modal v-model:show="showTaskLogModal" preset="card" :title="logModalTitle" :bordered="false" size="huge"
      style="max-width: 1200px; width: 95vw; height: 95vh; max-height: 95vh;--n-padding-bottom:8px"
      :segmented="{ content: true }" class="task-log-modal">
      <div class="enhanced-task-logs-container">
        <!-- 日志过滤器 -->
        <EnhancedLogFilter v-model:filters="logFilters" @search="handleLogSearch" @reset="handleLogReset"
          @export="handleLogExport" />

        <!-- 日志查看器 -->
        <div class="log-viewer-wrapper">
          <ConsoleLogViewer :logs="parsedLogLines" :searchTerm="logFilters.search"
            :levelFilter="logFilters.level || undefined" :showStats="false" :isRealTimeEnabled="isRealTimeEnabled"
            :logLoading="logLoading" :showRealTimeControls="true" @clear-logs="handleClearLogs"
            @toggle-real-time="toggleRealTimeUpdate" @refresh-logs="refreshLogs" />
        </div>

        <!-- 日志加载状态 -->
        <div v-if="logLoading" class="log-loading-overlay">
          <n-spin size="large">
            <template #description>
              正在加载日志数据...
            </template>
          </n-spin>
        </div>
      </div>


    </n-modal>

    <!-- 资源下载任务创建对话框已移除 -->
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref, watch, onUnmounted } from 'vue';
import { useClipboard } from '@vueuse/core';
import { useRouter } from 'vue-router';
import type { DataTableColumns, PaginationProps, SelectOption } from 'naive-ui';
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NEmpty,
  NGi,
  NGrid,
  NIcon,
  NInput,
  NModal,
  NPopconfirm,
  NProgress,
  NRadioButton,
  NRadioGroup,
  NSelect,
  NSpace,
  NStatistic,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  NAlert,
  NTooltip,
  useMessage,
  useDialog
} from 'naive-ui';
import { Icon } from '@iconify/vue';
import dayjs from 'dayjs';
import {
  getTaskList,
  getTaskStatus,
  getTaskFiles,
  getStrmDownloadUrl,
  cancelTask,
  continueTask,
  deleteTask,
  getTaskLogs
} from '@/service/api/strm';
import { formatDate } from '@/utils/common';
import { useLogStream, filterLogs, analyzeLogStats, exportLogsToFile } from '@/composables/useLogStream';
import TaskStatusDisplay from '@/components/custom/task-status-display.vue';
import ConsoleLogViewer from '@/components/custom/console-log-viewer.vue';
import EnhancedLogFilter from '@/components/custom/enhanced-log-filter.vue';
import FileTreeView from '@/components/custom/file-tree-view.vue';
import SegmentedProgressBar from '@/components/custom/segmented-progress-bar.vue';
import TaskFileList from '@/components/strm/TaskFileList.vue';

defineOptions({
  name: 'StrmTasks'
});

const message = useMessage();
const dialog = useDialog();
const router = useRouter();

// 初始化剪贴板功能
const { copy, isSupported } = useClipboard();
const loading = ref(false);
const tasksData = ref<any[]>([]);
const fileLoading = ref(false);

// 自动刷新相关状态
const autoRefreshEnabled = ref(true); // 默认开启
const refreshInterval = ref(2); // 刷新间隔（秒）
const refreshCountdown = ref(2); // 倒计时秒数
const refreshTimer = ref<NodeJS.Timeout | null>(null);
const countdownTimer = ref<NodeJS.Timeout | null>(null);

// 刷新间隔选项
const refreshIntervalOptions = [
  { label: '1秒', value: 1 },
  { label: '2秒', value: 2 },
  { label: '3秒', value: 3 },
  { label: '5秒', value: 5 },
  { label: '10秒', value: 10 },
  { label: '30秒', value: 30 }
];

// 实时日志流
const logStream = useLogStream();

// 任务详情相关
const showTaskDetailModal = ref(false);
const currentTask = ref<any>(null);
const activeTab = ref('overview');
const filesLoaded = ref(false);

// 文件列表分页状态
const fileListPage = ref(1);
const fileListPageSize = ref(10); // 表格视图默认10条
const fileListTotal = ref(0);

// 文件列表过滤状态
const currentFileFilters = ref<{ fileType?: string; search?: string; status?: boolean }>({});

// 任务列表分页配置
const pagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  itemCount: 0,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
  showQuickJumper: true
});

// 文件列表分页配置
const filePagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 50,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  itemCount: 0,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
  showQuickJumper: true
});

// 搜索参数
const searchValue = ref('');
const dateRange = ref<[number, number] | null>(null);
const statusFilter = ref<string | null>(null);

// 状态选项
const statusOptions: SelectOption[] = [
  { label: '等待中', value: 'PENDING' },
  { label: '处理中', value: 'RUNNING' },
  { label: '已完成', value: 'SUCCESS' },
  { label: '已取消', value: 'CANCELED' },
  { label: '失败', value: 'FAILED' }
];

// 日期快捷选项
const dateShortcuts = {
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
  },
  '最近7天': () => {
    const start = new Date();
    start.setDate(start.getDate() - 6);
    start.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setHours(23, 59, 59, 999);
    return [start.getTime(), end.getTime()] as [number, number];
  },
  '最近30天': () => {
    const start = new Date();
    start.setDate(start.getDate() - 29);
    start.setHours(0, 0, 0, 0);
    const end = new Date();
    end.setHours(23, 59, 59, 999);
    return [start.getTime(), end.getTime()] as [number, number];
  }
};

// 任务类型筛选已移除，所有任务统一为STRM处理任务
const taskTypeFilter = ref<string | null>(null);

// 获取任务列表
const fetchTasks = async () => {
  loading.value = true;
  try {
    const params: Record<string, any> = {
      page: pagination.page,
      page_size: pagination.pageSize
    };

    // 添加搜索条件
    if (searchValue.value) {
      params.search = searchValue.value;
    }

    // 添加状态过滤
    if (statusFilter.value) {
      params.status = statusFilter.value;
    }

    // 添加任务类型过滤
    if (taskTypeFilter.value) {
      params.task_type = taskTypeFilter.value;
    }

    // 添加日期范围过滤
    if (dateRange.value && Array.isArray(dateRange.value)) {
      const [start, end] = dateRange.value;
      if (start && end) {
        params.start_date = dayjs(start).format('YYYY-MM-DD');
        params.end_date = dayjs(end).format('YYYY-MM-DD 23:59:59');
      }
    }

    const response = await getTaskList(params);

    // 检查响应格式并提取数据
    if (response) {
      let tasksArray = [];
      let totalCount = 0;

      // 检查是否有嵌套的data对象（新格式）
      if (response.data) {
        // 如果data下有tasks数组
        if ((response.data as any).tasks && Array.isArray((response.data as any).tasks)) {
          tasksArray = (response.data as any).tasks;
          totalCount = (response.data as any).total || 0;
        }
        // 如果data本身就是任务数组
        else if (Array.isArray(response.data)) {
          tasksArray = response.data;
          totalCount = (response as any).total || 0;
        }
      }
      // 如果直接包含tasks数组（旧格式）
      else if ((response as any).tasks && Array.isArray((response as any).tasks)) {
        tasksArray = (response as any).tasks;
        totalCount = (response as any).total || 0;
      }
      // 如果response本身就是任务数组
      else if (Array.isArray(response)) {
        tasksArray = response;
        totalCount = tasksArray.length;
      }

      if (tasksArray.length > 0) {
        // 标准化任务数据
        tasksData.value = tasksArray.map((task: any) => ({
          ...task,
          // 如果后端没有提供task_type字段，默认为'strm'类型
          task_type: task.task_type || 'strm',
          // 确保状态字段统一为大写
          status: task.status ? String(task.status).toUpperCase() : 'UNKNOWN'
        }));

        pagination.itemCount = totalCount;
      } else {
        tasksData.value = [];
        pagination.itemCount = 0;
      }
    } else {
      console.error('获取任务列表失败：响应为空');
      message.error('获取任务列表失败：响应为空');
      tasksData.value = [];
      pagination.itemCount = 0;
    }
  } catch (error: any) {
    console.error('获取任务列表失败', error);
    if (error.response?.data) {
      console.error('响应数据:', error.response.data);
    }
    message.error(`获取任务列表失败: ${error.message || '未知错误'}`);
    tasksData.value = [];
    pagination.itemCount = 0;
  } finally {
    loading.value = false;
  }
};

// 获取任务详情
const fetchTaskDetail = async (taskId: number) => {
  try {
    loading.value = true;
    const response = await getTaskStatus(taskId);

    // 检查并提取任务详情
    if (response) {
      console.log('=== API响应完整数据结构 ===');
      console.log('response:', JSON.stringify(response, null, 2));
      console.log('response.data:', response.data);
      console.log('response.data类型:', typeof response.data);

      // 检查是否有嵌套的data对象
      if (response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
        currentTask.value = response.data;
        console.log('从response.data提取任务详情');
      } else {
        currentTask.value = response;
        console.log('直接使用response作为任务详情');
      }

      console.log('=== 提取后的任务数据 ===');
      console.log('currentTask.value:', JSON.stringify(currentTask.value, null, 2));

      // 设置默认任务类型
      if (!currentTask.value.task_type) {
        currentTask.value.task_type = 'strm';
      }

      // 将状态标准化为大写，并添加调试信息
      console.log('原始任务状态:', currentTask.value.status, '类型:', typeof currentTask.value.status);
      if (currentTask.value.status && typeof currentTask.value.status === 'string') {
        currentTask.value.status = currentTask.value.status.toUpperCase();
        console.log('标准化后的任务状态:', currentTask.value.status);
      } else {
        console.warn('任务状态为空或非字符串类型:', currentTask.value.status);
        // 如果状态为空或无效，设置默认状态
        currentTask.value.status = 'UNKNOWN';
      }

      // 对不同类型的任务可能需要做不同的处理
      if (currentTask.value.task_type === 'resource_download') {
        // 特殊处理资源下载任务的详情
        // ...
      }

      // 检查文件列表字段的各种可能位置
      console.log('=== 检查文件列表字段 ===');
      console.log('currentTask.value的所有键:', Object.keys(currentTask.value));
      console.log('currentTask.value.files:', currentTask.value.files);
      console.log('currentTask.value.file_list:', currentTask.value.file_list);
      console.log('currentTask.value.processed_files:', currentTask.value.processed_files);
      console.log('currentTask.value.task_files:', currentTask.value.task_files);
      console.log('currentTask.value.strm_files:', currentTask.value.strm_files);

      // 尝试从不同的字段获取文件列表
      let filesList = null;
      const possibleFields = ['files', 'file_list', 'processed_files', 'task_files', 'strm_files', 'result_files'];

      for (const field of possibleFields) {
        if (currentTask.value[field] && Array.isArray(currentTask.value[field])) {
          filesList = currentTask.value[field];
          console.log(`从 ${field} 字段获取文件列表，数量:`, filesList.length);
          break;
        }
      }

      if (filesList && filesList.length > 0) {
        currentTask.value.files = filesList;
        console.log('文件列表存在，数量:', filesList.length);
        console.log('文件列表示例数据:', filesList.slice(0, 2));
        filesLoaded.value = true;
      } else {
        console.warn('文件列表不存在或为空，设置为空数组');
        currentTask.value.files = [];
        filesLoaded.value = false;
      }

      // 重置标签页状态
      activeTab.value = 'overview';

      // 重置文件列表分页状态
      fileListPage.value = 1;
      fileListPageSize.value = 10; // 表格视图默认10条
      fileListTotal.value = 0;
      // 重置过滤状态
      currentFileFilters.value = {};

      showTaskDetailModal.value = true;
      console.log('任务详情获取完成，文件列表数量:', currentTask.value.files.length);
    } else {
      console.error('获取任务详情失败：响应为空');
      message.error('获取任务详情失败：响应为空');
    }
  } catch (error: any) {
    console.error('获取任务详情失败', error);
    if (error.response?.data) {
      console.error('响应数据:', error.response.data);
    }
    message.error(`获取任务详情失败: ${error.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
};



// 处理页码变化
const handlePageChange = (page: number) => {
  pagination.page = page;
  fetchTasks();
};

// 处理每页数量变化
const handlePageSizeChange = (pageSize: number) => {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  fetchTasks();
};

// 处理搜索
const handleSearch = () => {
  pagination.page = 1;
  fetchTasks();
};

// 清除筛选条件
const clearFilters = () => {
  searchValue.value = '';
  dateRange.value = null;
  statusFilter.value = null;
  taskTypeFilter.value = null;
  handleSearch();
};

// 跳转到生成页面
const goToGenerate = () => {
  router.push('/strm/generate');
};

// 跳转到任务的生成进度页面
const goToTaskProgress = (taskId: number) => {
  router.push(`/strm/generate?step=2&taskId=${taskId}`);
};

// 处理下载STRM文件
const handleDownload = (taskId: number) => {
  const url = getStrmDownloadUrl(taskId);
  window.open(url, '_blank');
};

// 处理取消任务
const handleCancelTask = async (taskId: number) => {
  try {
    await cancelTask(taskId);
    message.success('任务已取消');
    fetchTasks();
  } catch (error: any) {
    message.error(`取消任务失败: ${error.message || '未知错误'}`);
  }
};

// 处理删除任务
const handleDeleteTask = async (taskId: number) => {
  try {
    const response = await deleteTask(taskId);
    // 显示后端返回的详细消息
    const successMessage = response?.data?.message || '任务已删除';
    message.success(successMessage);
    fetchTasks();
  } catch (error: any) {
    message.error(`删除任务失败: ${error.message || '未知错误'}`);
  }
};

// 处理继续任务
const handleContinueTask = async (taskId: number) => {
  try {
    const response = await continueTask(taskId);
    // 显示后端返回的详细消息
    const successMessage = response?.data?.message || '任务已继续';
    message.success(successMessage);
    fetchTasks();
  } catch (error: any) {
    message.error(`继续任务失败: ${error.message || '未知错误'}`);
  }
};

// 获取总体成功文件数（STRM + 资源文件）
const getTotalSuccessFiles = (task: any) => {
  if (!task) return 0;
  const strmSuccess = task.strm_success || 0;
  const resourceSuccess = task.resource_success || 0;
  return strmSuccess + resourceSuccess;
};

// 获取总体失败文件数（STRM + 资源文件）
const getTotalFailedFiles = (task: any) => {
  if (!task) return 0;
  const strmFailed = task.strm_failed || 0;
  const resourceFailed = task.resource_failed || 0;
  return strmFailed + resourceFailed;
};

// 获取总体已处理文件数（成功 + 失败）
const getTotalProcessedFiles = (task: any) => {
  if (!task) return 0;
  return getTotalSuccessFiles(task) + getTotalFailedFiles(task);
};

// 获取任务总体进度百分比
const getTaskProgressPercentage = (task: any) => {
  if (!task) return 0;

  // 优先使用后端计算的进度（已修复为包含失败文件）
  if (task.progress !== undefined && task.progress !== null) {
    return Math.round(task.progress);
  }

  // 降级到前端计算（兼容旧数据）- 统计已处理的文件（成功+失败）
  const total = task.total_files || 0;
  const processed = getTotalProcessedFiles(task);
  return total > 0 ? Math.round((processed / total) * 100) : 0;
};

// 获取STRM文件进度百分比
const getStrmProgressPercentage = (task: any) => {
  if (!task) return 0;

  const total = task.strm_files_count || 0;
  const success = task.strm_success || 0;
  const failed = task.strm_failed || 0;

  // 如果没有STRM文件，返回100%
  if (total === 0) return 100;

  // 基于已处理文件数计算进度（成功+失败）
  const processed = success + failed;
  return total > 0 ? Math.round((processed / total) * 100) : 0;
};

// 获取资源文件进度百分比
const getResourceProgressPercentage = (task: any) => {
  if (!task) return 0;

  const total = task.resource_files_count || 0;
  const success = task.resource_success || 0;
  const failed = task.resource_failed || 0;

  // 如果没有资源文件，返回100%
  if (total === 0) return 100;

  // 基于已处理文件数计算进度（成功+失败）
  const processed = success + failed;
  return total > 0 ? Math.round((processed / total) * 100) : 0;
};

// 获取任务进度百分比文本（带%符号）
const getTaskProgressText = (task: any) => {
  // 使用不换行空格(\u00A0)连接数字和百分比符号
  return `${getTaskProgressPercentage(task)}\u00A0%`;
};

// 获取任务进度状态
const getTaskProgressStatus = (task: any): 'default' | 'success' | 'error' | 'warning' | 'info' => {
  const status = (task.status || '').toString().toUpperCase();

  // 处理不同的状态格式
  if (status === 'FAILED' || status === 'ERROR') return 'error';
  if (status === 'SUCCESS' || status === 'COMPLETED') return 'success';
  if (status === 'RUNNING' || status === 'PROCESSING' || status === 'IN_PROGRESS') return 'warning';
  if (status === 'CANCELED' || status === 'CANCELLED') return 'info';
  return 'default';
};

// 获取任务文件列表
const fetchTaskFiles = async (
  taskId?: number,
  page?: number,
  pageSize?: number,
  filters?: { fileType?: string; search?: string; status?: boolean }
) => {
  if (!taskId && !currentTask.value?.id) return;

  const targetTaskId = taskId || currentTask.value!.id;
  const currentPage = page || fileListPage.value;
  const currentPageSize = pageSize || fileListPageSize.value;
  const currentFilters = filters || currentFileFilters.value;

  fileLoading.value = true;
  try {
    // 使用专门的文件列表API，支持真正的后端分页和过滤
    console.log(`[文件列表] 请求参数: taskId=${targetTaskId}, page=${currentPage}, pageSize=${currentPageSize}, filters=`, currentFilters);
    const response = await getTaskFiles(targetTaskId, currentPage, currentPageSize, currentFilters);

    if (response && response.data) {
      const { files, stats, pagination } = response.data;
      console.log(`[文件列表] API响应: files数量=${files?.length}, pagination=`, pagination, 'stats=', stats);

      if (currentTask.value) {
        currentTask.value.files = files || [];
        // 优先使用 pagination.total 字段，如果没有则使用 stats.total
        fileListTotal.value = pagination?.total || stats?.total || 0;
        fileListPage.value = pagination?.page || currentPage;
        fileListPageSize.value = pagination?.page_size || currentPageSize;
        filesLoaded.value = true;
        console.log(`[文件列表] 设置完成: fileListPageSize=${fileListPageSize.value}, files数量=${currentTask.value.files.length}`);
      }
    } else {
      console.warn('文件列表API响应为空');
      if (currentTask.value) {
        currentTask.value.files = [];
        fileListTotal.value = 0;
      }
    }
  } catch (error) {
    console.error('获取任务文件列表失败', error);
    if (currentTask.value) {
      currentTask.value.files = [];
      fileListTotal.value = 0;
    }
  } finally {
    fileLoading.value = false;
  }
};

// 表格列定义
const columns: DataTableColumns<any> = [
  {
    title: 'ID',
    key: 'id',
    width: 80,
    align: 'center'
  },
  {
    title: '任务名称',
    key: 'name',
    width: 300,
    ellipsis: {
      tooltip: true
    },
    align: 'center',
    render(row) {
      return h(
        NButton,
        {
          text: true,
          type: 'primary',
          onClick: () => goToTaskProgress(row.id),
          style: {
            padding: '0',
            height: 'auto',
            fontSize: '14px'
          }
        },
        { default: () => row.name || `任务 ${row.id}` }
      );
    }
  },
  {
    title: '任务类型',
    key: 'task_type',
    width: 120,
    align: 'center',
    render(row) {
      return h('span', {}, 'STRM处理');
    }
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    align: 'center',
    render(row) {
      return h(TaskStatusDisplay, {
        status: row.status,
        task: row,
        taskType: row.task_type || 'strm'
      });
    }
  },
  {
    title: '处理进度',
    key: 'progress',
    width: 200,
    align: 'center',
    render(row) {
      const total = row.total_files || 0;
      // 使用成功文件数计算进度（后端已经修改processed_files为只统计成功的）
      const processed = row.processed_files || 0;
      const percentage = total ? Math.round((processed / total) * 100) : 0;

      let status: 'default' | 'success' | 'error' | 'warning' | 'info' = 'default';
      if (row.status === 'FAILED') {
        status = 'error';
      } else if (row.status === 'SUCCESS' || row.status === 'COMPLETED') {
        // 检查是否有失败的文件
        const failedFiles = row.failed_files || 0;
        const resourceFailed = row.resource_failed || 0;

        if (failedFiles > 0 || resourceFailed > 0) {
          status = 'warning'; // 部分成功
        } else {
          status = 'success'; // 完全成功
        }
      }

      return h('div', { class: 'flex flex-col items-center' }, [
        h(
          NProgress,
          {
            percentage,
            showIndicator: false,
            processing: row.status === 'RUNNING',
            type: 'line',
            status,
            style: 'width: 100%;'
          }
        ),
        h('div', { class: 'flex flex-col items-center mt-1' }, [
          h('span', { class: 'text-xs', style: 'white-space: nowrap;' }, `${percentage}%`),
          h('span', { class: 'text-xs text-gray-500' }, `${processed}/${total} 文件`)
        ])
      ]);
    }
  },
  {
    title: '开始时间',
    key: 'create_time',
    width: 180,
    align: 'center',
    render(row) {
      // 使用start_time作为创建时间的数据源
      const timeValue = row.start_time || row.create_time || row.created_at;
      return formatDate(timeValue);
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 190,
    align: 'center',
    fixed: 'right',
    render(row: any) {
      return h(
        NSpace,
        { justify: "center" },
        {
          default: () => [
            // 查看按钮
            h(
              NButton,
              {
                size: 'small',
                onClick: () => fetchTaskDetail(row.id),
              },
              { default: () => '详情' }
            ),
            // 日志按钮
            h(
              NButton,
              {
                size: 'small',
                onClick: () => openLogViewer(row.id),
                type: 'info',
              },
              { default: () => '日志' }
            ),
            row.status === 'SUCCESS' ?
              h(
                NButton,
                {
                  size: 'small',
                  type: 'success',
                  onClick: () => handleDownload(row.id)
                },
                { default: () => '下载' }
              ) : null,
            row.status === 'PENDING' || row.status === 'RUNNING' ?
              h(
                NPopconfirm,
                {
                  onPositiveClick: () => handleCancelTask(row.id)
                },
                {
                  default: () => '确定要取消此任务吗？',
                  trigger: () => h(
                    NButton,
                    {
                      size: 'small',
                      type: 'warning'
                    },
                    { default: () => '取消' }
                  )
                }
              ) : null,
            row.status === 'CANCELED' ?
              h(
                NPopconfirm,
                {
                  onPositiveClick: () => handleContinueTask(row.id)
                },
                {
                  default: () => '确定要继续此任务吗？',
                  trigger: () => h(
                    NButton,
                    {
                      size: 'small',
                      type: 'primary'
                    },
                    { default: () => '继续' }
                  )
                }
              ) : null,
            h(
              NPopconfirm,
              {
                onPositiveClick: () => handleDeleteTask(row.id)
              },
              {
                default: () => '确定要删除此任务吗？',
                trigger: () => h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error'
                  },
                  { default: () => '删除' }
                )
              }
            )
          ]
        }
      );
    }
  }
];



// 处理标签页切换
const handleTabChange = (tabName: string) => {
  activeTab.value = tabName;
  console.log('切换到标签页:', tabName);

  // 如果切换到文件列表标签页且文件列表尚未加载，则加载文件列表
  if (tabName === 'files' && !filesLoaded.value && currentTask.value?.id) {
    // 重置分页状态
    fileListPage.value = 1;
    fileListPageSize.value = 10; // 表格视图默认10条
    fileListTotal.value = 0;
    // 重置过滤状态
    currentFileFilters.value = {};
    fetchTaskFiles(currentTask.value.id, 1, 10, {});
  }
};

// 文件点击处理
const handleFileClick = (file: any) => {
  console.log('文件点击:', file);
  // 这里可以添加文件点击的具体处理逻辑
};

// 文件列表分页事件处理
const handleFilePageChange = (page: number) => {
  fileListPage.value = page;
  fetchTaskFiles(currentTask.value?.id, page, fileListPageSize.value, currentFileFilters.value);
};

const handleFilePageSizeChange = (pageSize: number) => {
  fileListPageSize.value = pageSize;
  fileListPage.value = 1; // 重置到第一页
  fetchTaskFiles(currentTask.value?.id, 1, pageSize, currentFileFilters.value);
};

// 文件过滤条件变化处理
const handleFileFilterChange = (filters: { fileType?: string; search?: string; status?: string }) => {
  currentFileFilters.value = filters;
  fileListPage.value = 1; // 重置到第一页
  fetchTaskFiles(currentTask.value?.id, 1, fileListPageSize.value, filters);
};

// 日志查看相关
const showTaskLogModal = ref(false);
const currentTaskId = ref<number | null>(null);
const logLoading = ref(false);
const logData = ref<any[]>([]);

// 日志过滤器状态
const logFilters = reactive({
  search: '',
  level: null as string | null,
  logType: null as string | null,
  timeRange: null as [number, number] | null,
  regex: '',
  exclude: ''
});

// 日志统计信息
const logStats = reactive({
  total: 0,
  filtered: 0,
  info: 0,
  warning: 0,
  error: 0,
  debug: 0
});



// 日志模态框标题
const logModalTitle = computed(() => {
  const taskName = currentTask.value?.name || `任务${currentTaskId.value}`;
  const status = isRealTimeEnabled.value ? ' (实时更新)' : '';
  return `${taskName} - 日志详情${status}`;
});

// 实时更新状态
const isRealTimeEnabled = ref(false);

// 解析后的日志行数据 - 用于控制台显示
const parsedLogLines = computed(() => {
  // 如果没有数据，返回空数组
  if (!logData.value || logData.value.length === 0) {
    return [];
  }

  // 将日志记录转换为纯文本行格式
  let logs = logData.value.map(line => {
    // 如果已经是字符串，直接返回
    if (typeof line === 'string') {
      return line;
    }

    // 兼容处理：如果是对象格式，则格式化（保留向后兼容性）
    const timestamp = line.timestamp ? formatDate(line.timestamp, 'YYYY-MM-DD HH:mm:ss') : '';
    const level = line.level || 'INFO';
    const message = line.message || '';

    // 构建日志行
    let logLine = `[${timestamp}] [${level}] ${message}`;

    // 添加文件路径信息（如果有）
    if (line.file_path) {
      logLine += ` | 文件: ${line.file_path}`;
    }

    // 添加目标路径信息（如果有）
    if (line.target_path) {
      logLine += ` | 目标: ${line.target_path}`;
    }

    // 添加错误信息（如果有）
    if (line.error_message) {
      logLine += ` | 错误: ${line.error_message}`;
    }

    // 添加状态信息（如果有）
    if (typeof line.is_success === 'boolean') {
      logLine += ` | 状态: ${line.is_success ? '成功' : '失败'}`;
    }

    // 返回日志行
    return logLine;
  });

  // 应用客户端过滤器（用于实时更新时的本地过滤）
  if (logFilters.search || logFilters.level || logFilters.exclude || logFilters.regex) {
    logs = filterLogs(logs, {
      search: logFilters.search,
      level: logFilters.level || undefined,
      exclude: logFilters.exclude,
      regex: logFilters.regex,
      timeRange: logFilters.timeRange ? [
        new Date(logFilters.timeRange[0]),
        new Date(logFilters.timeRange[1])
      ] : undefined
    });

    // 更新过滤后的统计信息
    logStats.filtered = logs.length;
  } else {
    logStats.filtered = logs.length;
  }

  return logs;
});

// 获取任务日志
const fetchTaskLogs = async () => {
  if (!currentTaskId.value) return;

  logLoading.value = true;
  try {
    const params: Record<string, any> = {};

    // 添加过滤参数
    if (logFilters.search) {
      params.search = logFilters.search;
    }

    if (logFilters.level) {
      params.level = logFilters.level;
    }

    if (logFilters.logType) {
      params.log_type = logFilters.logType;
    }

    // 添加时间范围过滤
    if (logFilters.timeRange) {
      params.start_time = new Date(logFilters.timeRange[0]).toISOString();
      params.end_time = new Date(logFilters.timeRange[1]).toISOString();
    }

    const { data } = await getTaskLogs(currentTaskId.value, params);
    if (data) {
      // 处理日志原始内容
      if (data.raw_content) {
        // 从raw_content分割日志行
        const logLines = data.raw_content.split('\n')
          .filter((line: string) => line.trim() !== '')
          .map((line: string) => line);

        logData.value = logLines;

        // 更新统计信息
        updateLogStats(logLines);
      } else {
        logData.value = [];
        resetLogStats();
      }
    }
  } catch (error: any) {
    message.error(`获取任务日志失败: ${error.message || '未知错误'}`);
    logData.value = [];
    resetLogStats();
  } finally {
    logLoading.value = false;
  }
};

// 更新日志统计信息
const updateLogStats = (logs: string[]) => {
  logStats.total = logs.length;
  logStats.filtered = logs.length;
  logStats.info = 0;
  logStats.warning = 0;
  logStats.error = 0;
  logStats.debug = 0;

  logs.forEach(line => {
    if (line.includes('[INFO]')) {
      logStats.info++;
    } else if (line.includes('[WARNING]')) {
      logStats.warning++;
    } else if (line.includes('[ERROR]')) {
      logStats.error++;
    } else if (line.includes('[DEBUG]')) {
      logStats.debug++;
    }
  });
};

// 重置日志统计信息
const resetLogStats = () => {
  Object.assign(logStats, {
    total: 0,
    filtered: 0,
    info: 0,
    warning: 0,
    error: 0,
    debug: 0
  });
};

// 处理日志搜索
const handleLogSearch = (filters?: any) => {
  if (filters) {
    Object.assign(logFilters, filters);
  }
  fetchTaskLogs();
};

// 处理日志重置
const handleLogReset = () => {
  Object.assign(logFilters, {
    search: '',
    level: null,
    logType: null,
    timeRange: null,
    regex: '',
    exclude: ''
  });
  fetchTaskLogs();
};

// 处理日志导出
const handleLogExport = async (filters?: any) => {
  if (!logData.value || logData.value.length === 0) {
    message.warning('暂无日志可导出');
    return;
  }

  try {
    const taskName = currentTask.value?.name || `任务${currentTaskId.value}`;
    const fileName = `${taskName}_日志_${formatDate(new Date(), 'YYYY-MM-DD_HH-mm')}.txt`;

    // 应用过滤器处理日志数据
    let filteredLogs = [...logData.value];

    if (filters?.search) {
      filteredLogs = filteredLogs.filter(log =>
        log.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    if (filters?.level) {
      filteredLogs = filteredLogs.filter(log =>
        log.includes(`[${filters.level}]`)
      );
    }

    if (filters?.exclude) {
      filteredLogs = filteredLogs.filter(log =>
        !log.toLowerCase().includes(filters.exclude.toLowerCase())
      );
    }

    // 创建导出内容
    const exportContent = [
      `# ${taskName} 日志导出`,
      `# 导出时间: ${formatDate(new Date(), 'YYYY-MM-DD HH:mm:ss')}`,
      `# 总日志数: ${logData.value.length}`,
      `# 导出日志数: ${filteredLogs.length}`,
      '',
      ...filteredLogs
    ].join('\n');

    // 创建Blob对象
    const blob = new Blob([exportContent], { type: 'text/plain;charset=utf-8' });

    // 创建下载链接
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = fileName;

    // 点击下载
    document.body.appendChild(link);
    link.click();

    // 清理
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);

    message.success(`日志导出成功，共导出 ${filteredLogs.length} 条日志`);
  } catch (error) {
    message.error('日志导出失败');
  }
};

// 清空日志
const handleClearLogs = () => {
  logData.value = [];
  resetLogStats();
  message.info('日志已清空');
};

// 刷新日志
const refreshLogs = () => {
  fetchTaskLogs();
};

// 切换实时更新
const toggleRealTimeUpdate = () => {
  if (!currentTaskId.value) return;

  if (isRealTimeEnabled.value) {
    // 停止实时更新
    logStream.stopStream();
    isRealTimeEnabled.value = false;
    message.info('已停止实时更新');
  } else {
    // 开始实时更新
    logStream.startStream({
      taskId: currentTaskId.value,
      interval: 3000, // 3秒更新一次
      maxRetries: 5,
      onLogUpdate: (logs) => {
        logData.value = logs;
        updateLogStats(logs);
      },
      onError: (error) => {
        message.error(`实时更新失败: ${error.message}`);
      }
    });
    isRealTimeEnabled.value = true;
    message.success('已开启实时更新');
  }
};

// 打开日志查看器
const openLogViewer = (taskId: number) => {
  currentTaskId.value = taskId;

  // 重置过滤器和统计信息（不调用fetchTaskLogs，避免重复请求）
  Object.assign(logFilters, {
    search: '',
    level: null,
    logType: null,
    timeRange: null,
    regex: '',
    exclude: ''
  });
  resetLogStats();

  // 停止之前的实时更新
  if (isRealTimeEnabled.value) {
    logStream.stopStream();
    isRealTimeEnabled.value = false;
  }

  showTaskLogModal.value = true;
  // 只调用一次fetchTaskLogs
  fetchTaskLogs();
};

// 监听日志模态框关闭，停止实时更新
watch(showTaskLogModal, (newValue) => {
  if (!newValue && isRealTimeEnabled.value) {
    // 模态框关闭时停止实时更新
    logStream.stopStream();
    isRealTimeEnabled.value = false;
  }
});

// 组件卸载时清理
onUnmounted(() => {
  if (isRealTimeEnabled.value) {
    logStream.stopStream();
  }
  // 清理自动刷新定时器
  stopAutoRefresh();
});

// 根据日志级别获取标签类型
const getLogLevelType = (level: string): 'success' | 'error' | 'warning' | 'info' | 'default' => {
  switch (level?.toUpperCase()) {
    case 'INFO':
      return 'info';
    case 'ERROR':
      return 'error';
    case 'WARNING':
      return 'warning';
    case 'DEBUG':
      return 'default';
    default:
      return 'default';
  }
};

// 旧的导出日志函数（保留兼容性）
const exportLogs = () => {
  handleLogExport(logFilters);
};

// 自动刷新相关函数
const startAutoRefresh = () => {
  if (!autoRefreshEnabled.value) return;

  // 清除现有定时器
  stopAutoRefresh();

  // 启动倒计时
  startCountdown();

  // 启动刷新定时器
  refreshTimer.value = setInterval(() => {
    if (autoRefreshEnabled.value) {
      fetchTasks().then(() => {
        // 刷新完成后重新启动倒计时
        startCountdown();
      });
    } else {
      // 如果自动刷新被关闭，停止刷新
      stopAutoRefresh();
    }
  }, refreshInterval.value * 1000); // 使用设定的间隔时间
};

const stopAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
  if (countdownTimer.value) {
    clearInterval(countdownTimer.value);
    countdownTimer.value = null;
  }
};

const startCountdown = () => {
  if (countdownTimer.value) {
    clearInterval(countdownTimer.value);
  }

  refreshCountdown.value = refreshInterval.value;
  countdownTimer.value = setInterval(() => {
    refreshCountdown.value--;
    if (refreshCountdown.value <= 0) {
      refreshCountdown.value = refreshInterval.value;
    }
  }, 1000);
};

const toggleAutoRefresh = (enabled: boolean) => {
  autoRefreshEnabled.value = enabled;
  if (enabled) {
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
};

// 更新刷新间隔
const updateRefreshInterval = (newInterval: number) => {
  refreshInterval.value = newInterval;
  refreshCountdown.value = newInterval;

  // 如果自动刷新正在运行，重新启动以应用新的间隔
  if (autoRefreshEnabled.value && refreshTimer.value) {
    startAutoRefresh();
  }
};

// 组件挂载时获取数据
onMounted(() => {
  fetchTasks().then(() => {
    // 初始加载完成后，如果开启了自动刷新，则启动自动刷新
    if (autoRefreshEnabled.value) {
      startAutoRefresh();
    }
  });
});

// 添加计算处理时长的辅助函数
const formatDuration = (seconds: number) => {
  if (seconds < 0) return '-'; // 处理异常情况

  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = Math.floor(seconds % 60);

  if (days > 0) {
    return `${days}天${hours}小时`;
  }

  if (hours > 0) {
    return `${hours}小时${minutes}分钟`;
  }

  if (minutes > 0) {
    return `${minutes}分钟${remainingSeconds}秒`;
  }

  // 当时间差小于1秒但大于0时，显示"不到1秒"而不是"0秒"
  if (seconds > 0 && remainingSeconds === 0) {
    return "不到1秒";
  }

  return `${remainingSeconds}秒`;
};

const isTaskProcessing = (task: any) => {
  return task.status === 'RUNNING';
};

// 获取状态图标
const getStatusIcon = (status: string) => {
  // 确保状态值为大写，并处理null或undefined情况
  const normalizedStatus = (status || '').toUpperCase();

  const statusMap: Record<string, string> = {
    'PENDING': 'mdi:clock-outline',
    'RUNNING': 'mdi:cog-play',
    'PROCESSING': 'mdi:cog-play',
    'IN_PROGRESS': 'mdi:cog-play',
    'SUCCESS': 'mdi:check-circle',
    'COMPLETED': 'mdi:check-circle',
    'FAILED': 'mdi:close-circle',
    'ERROR': 'mdi:close-circle',
    'CANCELLED': 'mdi:cancel',
    'CANCELED': 'mdi:cancel',
    'UNKNOWN': 'mdi:help-circle'
  };
  return statusMap[normalizedStatus] || 'mdi:help-circle';
};

// 获取状态文本
const getStatusText = (status: string) => {
  // 确保状态值为大写，并处理null或undefined情况
  const normalizedStatus = (status || '').toUpperCase();

  const statusMap: Record<string, string> = {
    'PENDING': '等待中',
    'RUNNING': '处理中',
    'PROCESSING': '处理中',
    'IN_PROGRESS': '处理中',
    'SUCCESS': '已完成',
    'COMPLETED': '已完成',
    'FAILED': '处理失败',
    'ERROR': '处理失败',
    'CANCELLED': '已取消',
    'CANCELED': '已取消',
    'UNKNOWN': '未知状态'
  };
  return statusMap[normalizedStatus] || `${normalizedStatus || '未知状态'}`;
};

// 获取状态描述
const getStatusDescription = (status: string) => {
  // 确保状态值为大写，并处理null或undefined情况
  const normalizedStatus = (status || '').toUpperCase();

  const statusMap: Record<string, string> = {
    'PENDING': '任务正在等待系统资源分配',
    'RUNNING': '任务正在处理中，请耐心等待',
    'PROCESSING': '任务正在处理中，请耐心等待',
    'IN_PROGRESS': '任务正在处理中，请耐心等待',
    'SUCCESS': '所有文件已成功处理完成',
    'COMPLETED': '任务已完成，可以查看结果',
    'FAILED': '任务处理过程中出现错误',
    'ERROR': '任务处理过程中出现错误',
    'CANCELLED': '任务已被用户或系统取消',
    'CANCELED': '任务已被用户或系统取消',
    'UNKNOWN': '无法识别的任务状态，请联系管理员'
  };
  return statusMap[normalizedStatus] || `状态信息未知 (${normalizedStatus || '空'})`;
};

const getTaskDuration = (task: any) => {
  if (!task.start_time) return '尚未开始';

  const start = new Date(task.start_time).getTime();

  // 如果任务已完成，计算开始到结束的时长
  if (task.end_time) {
    const end = new Date(task.end_time).getTime();
    const duration = (end - start) / 1000; // 转换为秒
    return formatDuration(duration);
  }

  // 如果任务正在进行中，计算开始到现在的时长，并标记为进行中
  if (isTaskProcessing(task)) {
    const now = new Date().getTime();
    const duration = (now - start) / 1000; // 转换为秒
    return `${formatDuration(duration)} (进行中)`;
  }

  return '尚未完成';
};

// 获取任务类型显示名称
const getTaskTypeDisplay = (taskType: string) => {
  const typeMap: Record<string, string> = {
    'strm': 'STRM处理任务',
    'resource_download': '资源下载任务',
    'batch_process': '批量处理任务'
  };
  return typeMap[taskType] || 'STRM处理任务';
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (!bytes || bytes === 0) return '0 B';

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
};



// 复制输出目录路径
const copyOutputDir = async () => {
  if (!currentTask.value?.output_dir) {
    message.warning('没有可复制的输出目录');
    return;
  }

  if (!isSupported) {
    message.error('您的浏览器不支持剪贴板功能');
    return;
  }

  const textToCopy = currentTask.value.output_dir;
  console.log('尝试复制文本:', textToCopy);

  try {
    await copy(textToCopy);
    console.log('文本:', textToCopy);
    message.success('输出目录路径已复制到剪贴板');
  } catch (error) {
    console.error('复制失败:', error);
    message.error('复制失败，请手动复制');

    // 如果复制失败，显示对话框让用户手动复制
    showCopyModal(textToCopy);
  }
};



// 显示复制模态框
const showCopyModal = (text: string) => {
  dialog.info({
    title: '复制输出目录路径',
    content: `请手动复制以下路径：\n\n${text}`,
    positiveText: '已复制',
    onPositiveClick: () => {
      message.success('感谢确认！');
    }
  });
};

// 获取文件名（从路径中提取）
const getFileName = (filePath: string) => {
  if (!filePath) return '未知文件';
  const parts = filePath.split(/[/\\]/);
  return parts[parts.length - 1] || filePath;
};

// 资源下载任务创建功能已移除，现在所有任务通过STRM处理任务统一处理
</script>

<style scoped>
/* 任务详情页面样式 */
.task-detail-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 0;
}

/* 任务头部样式 */
.task-detail-header {
  padding-bottom: 16px;
  border-bottom: 1px solid var(--n-border-color);
}

.task-header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-icon {
  font-size: 24px;
  margin-right: 12px;
}

.task-name {
  font-size: 20px;
  font-weight: 600;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 16px;
}

.task-meta-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.close-button {
  margin-left: 8px;
  transition: all 0.2s ease;
  font-size: 14px;
  font-weight: bold;
  color: #666;
}

.close-button:hover {
  background-color: rgba(0, 0, 0, 0.05);
  color: #333;
}

/* 任务状态横幅 */
.task-status-banner {
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.status-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status-title {
  font-size: 18px;
  font-weight: 600;
}

.status-subtitle {
  font-size: 14px;
  opacity: 0.8;
}

.status-progress {
  min-width: 200px;
  max-width: 300px;
}

.progress-text {
  margin-top: 8px;
  font-size: 13px;
  text-align: center;
}

/* 状态颜色 */
.status-pending {
  background-color: rgba(96, 125, 139, 0.1);
}

.status-running {
  background-color: rgba(24, 144, 255, 0.1);
}

.status-completed,
.status-success {
  background-color: rgba(82, 196, 26, 0.1);
}

.status-failed {
  background-color: rgba(245, 34, 45, 0.1);
}

.status-cancelled {
  background-color: rgba(250, 173, 20, 0.1);
}

.status-unknown {
  background-color: rgba(140, 140, 140, 0.1);
}

/* 统计卡片网格 */
.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 24px;
}

.stat-card-group {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border-radius: 8px;
  background-color: var(--n-card-color);
  border: 1px solid var(--n-border-color);
}

/* 优化的圆形进度条区域样式 */
.optimized-progress-area {
  margin-bottom: 24px;
}

.circular-progress-container {
  padding: 16px 0;
}

/* 文件统计与处理进度样式 */
.progress-stats-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 20px 0;
  color: var(--n-text-color);
}

.progress-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 20px;
}

.progress-card {
  background: var(--n-card-color);
  border: 1px solid var(--n-border-color);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.progress-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.progress-card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
  min-width: 0;
  /* 允许flex子元素收缩 */
}

.progress-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  flex-shrink: 0;
}

.progress-card-title {
  flex: 1;
  min-width: 0;
  /* 允许收缩 */
  overflow: hidden;
  /* 防止内容溢出 */
}

.progress-card-title h4 {
  margin: 0 0 4px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--n-text-color);
}

.progress-card-subtitle {
  font-size: 13px;
  color: var(--n-text-color-2);
}

.progress-card-percentage {
  font-size: 24px;
  font-weight: 700;
  color: var(--n-text-color);
  line-height: 1;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 60px;
  /* 确保能容纳"100%"的宽度 */
  text-align: right;
  /* 右对齐显示 */
}

.progress-card-body {
  margin-top: 16px;
  white-space: nowrap;
}

.progress-card-stats {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  gap: 16px;
}

.progress-card-stats .stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.progress-card-stats .stat-label {
  font-size: 12px;
  color: var(--n-text-color-2);
  font-weight: 500;
}

.progress-card-stats .stat-value {
  font-size: 16px;
  font-weight: 600;
}

.progress-card-stats .stat-value.success {
  color: #52c41a;
}

.progress-card-stats .stat-value.error {
  color: #f5222d;
}

/* 不同类型卡片的图标颜色 */
.progress-card.overall .progress-card-icon {
  background: linear-gradient(135deg, rgba(114, 46, 209, 0.1), rgba(114, 46, 209, 0.2));
  color: #722ed1;
}

.progress-card.strm .progress-card-icon {
  background: linear-gradient(135deg, rgba(82, 196, 26, 0.1), rgba(82, 196, 26, 0.2));
  color: #52c41a;
}

.progress-card.resource .progress-card-icon {
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1), rgba(24, 144, 255, 0.2));
  color: #1890ff;
}

/* 响应式样式 */
@media (max-width: 768px) {
  .progress-stats-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .progress-card-header {
    gap: 12px;
  }

  .progress-card-icon {
    width: 40px;
    height: 40px;
  }

  .progress-card-percentage {
    font-size: 20px;
  }

  .progress-card-stats {
    gap: 12px;
  }
}

@media (max-width: 480px) {
  .progress-card {
    padding: 16px;
  }

  .progress-card-header {
    flex-direction: row;
    align-items: flex-start;
    gap: 12px;
    flex-wrap: nowrap;
    /* 防止换行 */
  }

  .progress-card-icon {
    width: 40px;
    height: 40px;
  }

  .progress-card-percentage {
    font-size: 20px;
    white-space: nowrap;
    flex-shrink: 0;
    min-width: 50px;
    /* 移动端稍小一些但仍能容纳"100%" */
    text-align: right;
  }
}

/* 重构后的任务信息部分 */
.task-info-section {
  margin-bottom: 32px;
}

/* 标题包装器 */
.section-title-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid var(--n-divider-color);
}

.section-title-wrapper .section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 700;
  color: var(--n-text-color);
  margin: 0;
}

.title-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(24, 144, 255, 0.1), rgba(24, 144, 255, 0.2));
  color: #1890ff;
}

.task-status-badge {
  display: flex;
  align-items: center;
}

/* 增强的信息网格 */
.enhanced-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

/* 信息卡片 */
.info-card {
  background: var(--n-card-color);
  border: 1px solid var(--n-border-color);
  border-radius: 16px;
  padding: 24px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.info-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, transparent, var(--accent-color), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.info-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.1);
}

.info-card:hover::before {
  opacity: 1;
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  flex-shrink: 0;
}

.card-title h4 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--n-text-color);
}

.card-subtitle {
  font-size: 13px;
  color: var(--n-text-color-2);
  opacity: 0.8;
}

/* 不同类型卡片的样式 */
.primary-card {
  --accent-color: #722ed1;
}

.primary-icon {
  background: linear-gradient(135deg, rgba(114, 46, 209, 0.1), rgba(114, 46, 209, 0.2));
  color: #722ed1;
}

.time-card {
  --accent-color: #13c2c2;
}

.time-icon {
  background: linear-gradient(135deg, rgba(19, 194, 194, 0.1), rgba(19, 194, 194, 0.2));
  color: #13c2c2;
}

/* 卡片内容 */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 信息行 */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--n-modal-color);
  border-radius: 10px;
  border: 1px solid var(--n-divider-color);
  transition: all 0.2s ease;
}

.info-row:hover {
  background: var(--n-hover-color);
  border-color: var(--accent-color);
}

.info-row.full-width {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--n-text-color-2);
  min-width: 0;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color);
  text-align: right;
  min-width: 0;
}

.info-value.highlight {
  color: #722ed1;
  font-weight: 700;
}

.info-value.server-name {
  color: #52c41a;
  font-weight: 600;
}

.server-note {
  font-size: 12px;
  color: var(--n-text-color-3);
  font-weight: 400;
  margin-left: 8px;
}



.info-value.time-value {
  color: #fa8c16;
  font-weight: 600;
}

.info-value.duration-value {
  color: #1890ff;
  font-weight: 600;
}

.output-dir-container {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.path-input {
  flex: 1;
}

.path-input {
  cursor: pointer;
}

.path-input :deep(.n-input__input-el) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.path-input:hover :deep(.n-input__input-el) {
  background: rgba(24, 144, 255, 0.05);
  border-color: #1890ff;
}

.path-input:active :deep(.n-input__input-el) {
  background: rgba(24, 144, 255, 0.1);
}

.info-value.path-value {
  word-break: break-all;
  text-align: left;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  background: rgba(0, 0, 0, 0.05);
  padding: 8px 12px;
  border-radius: 8px;
  flex: 1;
  overflow-x: auto;
  transition: all 0.2s ease;
  user-select: all;
}

.info-value.path-value.clickable {
  cursor: pointer;
  border: 1px solid transparent;
}

.info-value.path-value.clickable:hover {
  background: rgba(24, 144, 255, 0.1);
  border-color: #1890ff;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.2);
}

.info-value.path-value.clickable:active {
  transform: translateY(0);
  background: rgba(24, 144, 255, 0.15);
}

.copy-btn {
  flex-shrink: 0;
  font-size: 12px;
  padding: 4px 12px;
}

.info-value.server-url {
  color: #1890ff;
  font-weight: 600;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  word-break: break-all;
}

/* 美化的输出目录样式 */
.enhanced-output-dir {
  width: 100%;
  margin-top: 8px;
}

.path-display-container {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #f8faff 0%, #f0f7ff 100%);
  border: 1px solid #e1f0ff;
  border-radius: 12px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.path-display-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #1890ff, #40a9ff, #69c0ff);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.path-display-container:hover {
  border-color: #1890ff;
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.1);
  transform: translateY(-1px);
}

.path-display-container:hover::before {
  opacity: 1;
}

.path-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(24, 144, 255, 0.1);
  border-radius: 10px;
  margin-top: 2px;
}

.path-content {
  flex: 1;
  min-width: 0;
}

.path-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  font-weight: 500;
  color: #2c3e50;
  word-break: break-all;
  line-height: 1.5;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  border: 1px solid rgba(24, 144, 255, 0.1);
  cursor: text;
  user-select: all;
}

.path-text:hover {
  background: rgba(255, 255, 255, 1);
  border-color: rgba(24, 144, 255, 0.3);
}

.path-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.copy-action,
.open-action {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.copy-action:hover {
  background: rgba(24, 144, 255, 0.1);
  transform: translateY(-1px);
}

.open-action:hover {
  background: rgba(82, 196, 26, 0.1);
  transform: translateY(-1px);
}

.processing-status {
  animation: pulse 2s infinite;
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.6;
  }
}



/* 响应式设计 */
@media (max-width: 1200px) {
  .enhanced-info-grid {
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 20px;
  }
}

@media (max-width: 768px) {
  .section-title-wrapper {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .enhanced-info-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .info-card {
    padding: 20px;
  }

  .card-header {
    gap: 12px;
    margin-bottom: 16px;
  }

  .card-icon {
    width: 40px;
    height: 40px;
  }

  .card-title h4 {
    font-size: 16px;
  }

  .info-row {
    padding: 10px 12px;
  }

  .info-label {
    font-size: 13px;
  }

  .info-value {
    font-size: 13px;
  }

  /* 输出目录响应式样式 */
  .path-display-container {
    padding: 12px;
    gap: 8px;
  }

  .path-icon {
    width: 32px;
    height: 32px;
  }

  .path-text {
    font-size: 12px;
    padding: 6px 8px;
    margin-bottom: 8px;
  }

  .path-actions {
    gap: 6px;
  }

  .copy-action,
  .open-action {
    font-size: 11px;
    padding: 3px 6px;
  }

}

@media (max-width: 480px) {
  .task-info-section {
    margin-bottom: 24px;
  }

  .section-title-wrapper {
    margin-bottom: 20px;
    padding-bottom: 12px;
  }

  .section-title-wrapper .section-title {
    font-size: 18px;
    gap: 10px;
  }

  .title-icon-wrapper {
    width: 36px;
    height: 36px;
  }

  .info-card {
    padding: 16px;
    border-radius: 12px;
  }

  .card-header {
    gap: 10px;
    margin-bottom: 12px;
  }

  .card-icon {
    width: 36px;
    height: 36px;
  }

  .card-title h4 {
    font-size: 15px;
  }

  .card-subtitle {
    font-size: 12px;
  }

  .info-row {
    padding: 8px 10px;
    border-radius: 8px;
  }

  .info-label {
    font-size: 12px;
  }

  .info-value {
    font-size: 12px;
  }

  .info-value.path-value {
    font-size: 11px;
  }


}





/* 任务操作 */
.task-actions {
  margin-bottom: 24px;
  padding: 16px;
  border-radius: 8px;
  background-color: var(--n-card-color);
  border: 1px solid var(--n-border-color);
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
}



.text-success {
  color: #2ab85e;
}

.text-error {
  color: #f5222d;
}

.text-secondary-text {
  color: #8c8c8c;
}

.processing-status {
  color: #faad14;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 0.6;
  }

  50% {
    opacity: 1;
  }

  100% {
    opacity: 0.6;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .task-header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .status-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .status-progress {
    min-width: 100%;
    max-width: 100%;
  }



  .info-grid {
    grid-template-columns: 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}



.mb-4 {
  margin-bottom: 16px;
}

.mt-2 {
  margin-top: 8px;
}

.mr-1 {
  margin-right: 4px;
}

.text-center {
  text-align: center;
}

.text-lg {
  font-size: 18px;
}

.text-2xl {
  font-size: 24px;
}

.font-bold {
  font-weight: 700;
}

.font-medium {
  font-weight: 500;
}

.percent-text {
  font-size: 24px;
  font-weight: 700;
  white-space: nowrap;
  line-height: 1.2;
}

.no-wrap {
  white-space: nowrap;
}

.min-h-300px {
  min-height: 300px;
}

.tree-view-container {
  padding: 16px 0;
}

/* 增强的日志界面样式 */
.enhanced-task-logs-container {
  display: flex;
  flex-direction: column;
  height: calc(95vh - 80px);
  /* 减去模态框头部的高度，无需为底部footer预留空间 */
  max-height: calc(95vh - 80px);
  gap: 8px;
  position: relative;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
  box-sizing: border-box;
  padding: 0;
}

.log-viewer-wrapper {
  flex: 1;
  overflow: hidden;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: white;
  border: 1px solid #e8e8e8;
  height: 100%;
}

.log-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(4px);
}



/* 任务日志模态框样式 */
.task-log-modal {
  display: flex;
  flex-direction: column;
  height: 90vh;
  max-height: 90vh;
}

.task-log-modal :deep(.n-card) {
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
}

.task-log-modal :deep(.n-card__content) {
  flex: 1;
  overflow: hidden;
  padding: 16px !important;
  display: flex;
  flex-direction: column;
  min-height: 0;
}



.grid {
  display: grid;
}

.grid-cols-1 {
  grid-template-columns: repeat(1, minmax(0, 1fr));
}

.gap-4 {
  gap: 16px;
}

/* 统计网格响应式样式 */
.stat-grid {
  display: grid;
  gap: 16px;
}

/* 小屏幕：2列 */
@media (max-width: 767px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* 中等屏幕：3列 */
@media (min-width: 768px) and (max-width: 1023px) {
  .stat-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .md\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

/* 大屏幕：6列 */
@media (min-width: 1024px) {
  .stat-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

/* 文件列表占位符样式 */
.file-list-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 40px 20px;
}

/* 日志模态框响应式设计 */
@media (max-width: 768px) {
  .enhanced-task-logs-container {
    gap: 12px;
  }

  .log-viewer-wrapper {
    border-radius: 4px;
  }
}

/* 确保模态框内容不会溢出 */
.n-modal .n-card .n-card__content {
  overflow: hidden;
  max-width: 100%;
  box-sizing: border-box;
}

/* 针对日志模态框的特殊样式 */
.n-modal[style*="max-width: 1200px"] .n-card__content {
  padding: 16px;
  overflow: hidden;
}

/* 确保日志查看器组件充分利用空间 */
.log-viewer-wrapper :deep(.enhanced-log-viewer) {
  height: 100%;
  min-height: 400px;
}

.log-viewer-wrapper :deep(.log-content-wrapper) {
  flex: 1;
  min-height: 300px;
}

.log-viewer-wrapper :deep(.console-mode) {
  min-height: 300px;
  max-height: none;
}

/* 自动刷新控制样式 */
.auto-refresh-control {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--n-card-color);
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  transition: all 0.3s ease;
}

.auto-refresh-control:hover {
  border-color: var(--n-primary-color);
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.1);
}

.refresh-status {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 60px;
}

.refresh-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--n-text-color-2);
  line-height: 1;
}

.refresh-countdown {
  font-size: 11px;
  font-weight: 600;
  color: var(--n-primary-color);
  line-height: 1;
  animation: pulse-countdown 1s infinite;
}

.refresh-disabled {
  font-size: 11px;
  font-weight: 500;
  color: var(--n-text-color-3);
  line-height: 1;
}

@keyframes pulse-countdown {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .auto-refresh-control {
    padding: 4px 8px;
    gap: 6px;
  }

  .refresh-status {
    min-width: 50px;
  }

  .refresh-label {
    font-size: 11px;
  }

  .refresh-countdown,
  .refresh-disabled {
    font-size: 10px;
  }
}
</style>
