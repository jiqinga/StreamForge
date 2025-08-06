<template>
    <div class="h-full p-16px">
        <n-card title="STRM文件生成" :bordered="false" class="h-full rounded-8px shadow-sm">
            <!-- 步骤指示器：从垂直变为水平 -->
            <n-steps :current="highlightStep" :status="stepStatus" class="mb-24px">
                <n-step title="选择文件" description="选择已解析的文件" />
                <n-step title="配置服务器" description="选择服务器和生成选项" />
                <n-step title="生成进度" description="文件生成进度和结果" />
            </n-steps>

            <!-- 步骤内容区 -->
            <div class="step-content-area">
                <!-- 步骤1：文件选择 -->
                <div v-if="currentStep === 0" class="step-content">
                    <n-card title="选择文件" class="mb-16px">
                        <n-form label-placement="left" label-width="120px">
                            <n-form-item label="文件选择">
                                <n-select v-model:value="selectedFileId" :options="fileOptions"
                                    placeholder="请选择已解析的115目录树文件" :loading="filesLoading" filterable clearable
                                    @update:value="handleFileSelected" />
                            </n-form-item>
                        </n-form>
                    </n-card>

                    <!-- 文件统计信息卡片 -->
                    <n-card v-if="fileStats" title="文件统计" class="mb-16px">
                        <n-grid :cols="7" :x-gap="12" :y-gap="8">
                            <n-grid-item>
                                <n-statistic label="总文件数" :value="fileStats.total" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="视频文件" :value="fileStats.video" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="音频文件" :value="fileStats.audio" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="图片文件" :value="fileStats.image" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="字幕文件" :value="fileStats.subtitle" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="元数据" :value="fileStats.metadata || 0" />
                            </n-grid-item>
                            <n-grid-item>
                                <n-statistic label="其他" :value="fileStats.other || 0" />
                            </n-grid-item>
                        </n-grid>

                        <div v-if="fileStats && fileStats.video === 0" class="mt-16px">
                            <n-alert type="warning">
                                <template #icon>
                                    <icon-mdi-alert-circle />
                                </template>
                                当前文件中没有视频文件，无法生成STRM文件
                            </n-alert>
                        </div>
                    </n-card>

                    <!-- 操作按钮 -->
                    <div class="flex justify-end">
                        <n-button type="primary" :disabled="!selectedFileId || !fileStats || fileStats.video === 0"
                            @click="handleNextStep">
                            <template #icon>
                                <icon-mdi-arrow-right />
                            </template>
                            下一步：配置服务器
                        </n-button>
                    </div>
                </div>

                <!-- 步骤2：配置服务器 -->
                <div v-if="currentStep === 1" class="step-content">
                    <n-card title="服务器设置" class="mb-16px">
                        <n-form ref="formRef" :model="formModel" label-placement="left" label-width="120px">
                            <n-grid :cols="2" :x-gap="16">
                                <n-grid-item>
                                    <n-form-item label="媒体服务器" path="serverId">
                                        <n-select v-model:value="formModel.serverId" :options="serverOptions"
                                            placeholder="请选择媒体服务器" :loading="serversLoading" filterable clearable />
                                    </n-form-item>
                                </n-grid-item>
                                <n-grid-item>
                                    <n-form-item label="下载服务器" path="downloadServerId">
                                        <n-select v-model:value="formModel.downloadServerId"
                                            :options="downloadServerOptions" placeholder="请选择下载服务器"
                                            :loading="serversLoading" filterable clearable />
                                    </n-form-item>
                                </n-grid-item>
                            </n-grid>

                            <n-form-item label="任务名称" path="name">
                                <n-input v-model:value="formModel.name" placeholder="自定义任务名称（可选）" />
                            </n-form-item>
                        </n-form>
                    </n-card>

                    <!-- 操作按钮 -->
                    <div class="flex justify-between">
                        <n-button @click="currentStep = 0">
                            <template #icon>
                                <icon-mdi-arrow-left />
                            </template>
                            上一步
                        </n-button>
                        <n-button type="primary" :loading="generating"
                            :disabled="!formModel.serverId || !formModel.downloadServerId" @click="handleGenerateStrm">
                            <template #icon>
                                <icon-mdi-play />
                            </template>
                            开始生成
                        </n-button>
                    </div>
                </div>

                <!-- 步骤3：生成进度 -->
                <div v-if="currentStep === 2" class="step-content">
                    <n-card title="任务进度" class="mb-16px">
                        <!-- 任务基本信息区域 -->
                        <div class="task-header flex justify-between mb-16px items-center">
                            <div>
                                <div class="text-18px font-medium">{{ taskInfo.name }}</div>
                                <div class="text-14px text-secondary-text mt-4px flex items-center">
                                    <n-tag :type="getStatusTagType(taskInfo.status)" class="mr-2">
                                        {{ getStatusText(taskInfo.status) }}
                                    </n-tag>
                                    <span class="text-secondary-text">{{ lastUpdateTimeText }}</span>
                                </div>
                            </div>
                            <div>
                                <n-space align="center">
                                    <n-button
                                        size="small"
                                        @click="handleManualRefresh"
                                        :loading="refreshing"
                                        type="info"
                                        ghost
                                        class="flex items-center"
                                    >
                                        <template #icon>
                                            <Icon icon="mdi:refresh" />
                                        </template>
                                        立即刷新
                                    </n-button>

                                    <n-button
                                        size="small"
                                        type="info"
                                        ghost
                                        class="flex items-center"
                                    >
                                        <template #icon>
                                            <Icon icon="mdi:autorenew" />
                                        </template>
                                        自动刷新
                                        <n-switch
                                            v-model:value="autoRefresh"
                                            @update:value="toggleAutoRefresh"
                                            class="ml-8px"
                                        >
                                            <template #checked>开</template>
                                            <template #unchecked>关</template>
                                        </n-switch>
                                    </n-button>
                                </n-space>
                            </div>
                        </div>

                        <!-- 进度条 -->
                        <div class="progress-section mb-16px">
                            <n-progress
                                type="line"
                                :percentage="taskInfo.progress"
                                :indicator-placement="'inside'"
                                :processing="taskInfo.status === 'running'"
                                :height="20"
                                class="progress-bar"
                            />
                        </div>

                        <n-divider>文件统计</n-divider>

                        <!-- 文件统计信息区域 -->
                        <div class="stats-section mb-16px">
                            <n-grid :cols="4" :x-gap="16" :y-gap="16">
                                <n-grid-item>
                                    <div class="stat-card">
                                        <div class="stat-label">总文件数</div>
                                        <div class="stat-value">{{ taskInfo.total_files || 0 }}</div>
                                    </div>
                                </n-grid-item>
                                <n-grid-item>
                                    <div class="stat-card">
                                        <div class="stat-label">STRM文件数</div>
                                        <div class="stat-value">{{ taskInfo.strm_files_count || 0 }}</div>
                                    </div>
                                </n-grid-item>
                                <n-grid-item>
                                    <div class="stat-card">
                                        <div class="stat-label">资源文件数</div>
                                        <div class="stat-value">{{ taskInfo.resource_files_count || 0 }}</div>
                                    </div>
                                </n-grid-item>
                                <n-grid-item>
                                    <div class="stat-card">
                                        <div class="stat-label">耗时</div>
                                        <div class="stat-value">{{ taskInfo.elapsed_time || '00:00:00' }}</div>
                                    </div>
                                </n-grid-item>
                            </n-grid>
                        </div>

                        <!-- 成功/失败统计 -->
                        <div class="status-stats mb-16px">
                            <n-grid :cols="2" :x-gap="16" :y-gap="16">
                                <n-grid-item>
                                    <div class="status-card">
                                        <div class="status-header">STRM状态</div>
                                        <div class="status-content">
                                            <div class="status-item success">
                                                <span class="label">成功：</span>
                                                <span class="value">{{ taskInfo.strm_success || 0 }} / {{ taskInfo.strm_files_count || 0 }}</span>
                                            </div>
                                            <div class="status-item error">
                                                <span class="label">失败：</span>
                                                <span class="value">{{ taskInfo.strm_failed || 0 }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </n-grid-item>
                                <n-grid-item>
                                    <div class="status-card">
                                        <div class="status-header">资源状态</div>
                                        <div class="status-content">
                                            <div class="status-item success">
                                                <span class="label">成功：</span>
                                                <span class="value">{{ taskInfo.resource_success || 0 }} / {{ taskInfo.resource_files_count || 0 }}</span>
                                            </div>
                                            <div class="status-item error">
                                                <span class="label">失败：</span>
                                                <span class="value">{{ taskInfo.resource_failed || 0 }}</span>
                                            </div>
                                        </div>
                                    </div>
                                </n-grid-item>
                            </n-grid>
                        </div>

                        <!-- 错误信息 -->
                        <div v-if="taskInfo.error" class="error-section mb-16px">
                            <n-alert title="处理出错" type="error">
                                {{ taskInfo.error }}
                            </n-alert>
                        </div>

                        <n-divider>操作</n-divider>

                        <!-- 操作按钮 -->
                        <div class="action-section">
                            <n-space justify="center">
                                <n-button type="primary" :disabled="!isTaskCompleted || !hasSuccessFiles"
                                    @click="downloadFiles" size="large">
                                    <template #icon>
                                        <icon-mdi-download />
                                    </template>
                                    下载文件
                                </n-button>
                                <n-button type="error" :disabled="!isTaskActive" @click="handleCancelTask" size="large">
                                    <template #icon>
                                        <icon-mdi-cancel />
                                    </template>
                                    取消任务
                                </n-button>
                                <n-button @click="goToHistory" size="large">
                                    <template #icon>
                                        <icon-mdi-history />
                                    </template>
                                    历史任务
                                </n-button>
                            </n-space>
                        </div>
                    </n-card>
                </div>
            </div>
        </n-card>
    </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onUnmounted, onBeforeUnmount, computed, watch } from 'vue';
import { useRouter, useRoute, onBeforeRouteLeave } from 'vue-router';
import { useMessage } from 'naive-ui';
import { Icon } from '@iconify/vue';
import type { FormInst, SelectOption, StepsProps } from 'naive-ui';
import {
    getUploadHistory,
    getParseResult,
    getMediaServers,
    generateStrm,
    getTaskStatus,
    cancelTask,
    getSystemSettings,
    getStrmDownloadUrl as getStrmDownloadUrlApi
} from '@/service/api/strm';
// 已使用@iconify/vue的Icon组件，无需额外导入

defineOptions({
    name: 'StrmGenerate'
});

// 路由
const router = useRouter();
const route = useRoute();
const message = useMessage();

// 步骤控制
const currentStep = ref(0);
const stepStatus = ref<StepsProps['status']>('process');

// 计算属性：修正步骤高亮，使其与当前内容显示步骤一致
const highlightStep = computed(() => {
    // 添加1，使步骤指示器正确高亮当前步骤
    return currentStep.value + 1;
});

// 文件选择相关
const filesLoading = ref(false);
const fileOptions = ref<SelectOption[]>([]);
const selectedFileId = ref<number | null>(null);
const fileStats = ref<StrmAPI.ParseStats | null>(null);

// 系统设置相关
const systemSettings = ref<Record<string, any> | null>(null);

// 服务器选择相关
const serversLoading = ref(false);
const serverOptions = ref<SelectOption[]>([]);
const downloadServerOptions = ref<SelectOption[]>([]);
const formRef = ref<FormInst | null>(null);
const formModel = ref({
    serverId: null as number | null,
    downloadServerId: null as number | null,
    name: ''
});

// 任务生成相关
const generating = ref(false);
const taskPolling = ref(false);
const refreshing = ref(false);
// 定义最大无更新计数
const MAX_NO_UPDATE_COUNT = 10; // 连续10次无更新后触发警告
const noUpdateCounter = ref(0);
const lastUpdateTime = ref<Date | null>(null);
const taskInfo = ref<StrmAPI.StrmTaskDetail>({
    id: 0,
    name: '',
    status: 'pending',
    task_type: 'strm',
    total_files: 0,
    processed_files: 0,
    success_files: 0,
    failed_files: 0,
    progress: 0,
    output_dir: '',
    files: [],
    file_count: 0,
    resource_files_count: 0,
    strm_files_count: 0,
    strm_success: 0,
    strm_failed: 0,
    resource_success: 0,
    resource_failed: 0,
    video_files_count: 0
});

// 获取最后更新时间文本
const lastUpdateTimeText = computed(() => {
    if (!lastUpdateTime.value) return '等待更新...';

    // 计算时间差
    const now = new Date();
    const diff = Math.floor((now.getTime() - lastUpdateTime.value.getTime()) / 1000);

    if (diff < 5) return '刚刚更新';
    if (diff < 60) return `${diff}秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`;
    return formatDateTime(lastUpdateTime.value.toISOString());
});

// 状态文本映射
const STATUS_TEXT = {
    pending: '等待开始',
    running: '正在生成',
    completed: '生成完成',
    failed: '生成失败',
    canceled: '已取消'
};

// 添加自动刷新控制
const autoRefresh = ref(true); // 默认始终开启自动刷新
const refreshIntervalBase = ref(1000); // 固定刷新间隔为1秒
let refreshTimer: number | null = null; // 刷新定时器

// 获取已上传且已解析的文件列表
const fetchFiles = async () => {
    filesLoading.value = true;
    try {
        const res = await getUploadHistory({
            page: 1,
            page_size: 20
        });

        const records = res.data.records || [];
        // 筛选已解析的文件
        const parsedRecords = records.filter(record => record.status === 'parsed');

        // 转换为选择框选项
        fileOptions.value = parsedRecords.map((record: StrmAPI.UploadRecord) => ({
            label: record.filename,
            value: record.id,
            disabled: false
        }));

        if (fileOptions.value.length === 0) {
            message.warning('没有找到已解析的文件，请先上传并解析文件');
        }
    } catch (error: any) {
        message.error(error.message || '获取文件列表失败');
    } finally {
        filesLoading.value = false;
    }
};

// 获取系统设置
const fetchSystemSettings = async () => {
    try {
        const res = await getSystemSettings();
        systemSettings.value = res.data || null;
    } catch (error: any) {
        message.error(error.message || '获取系统设置失败');
    }
};

// 获取媒体服务器列表
const fetchServers = async () => {
    serversLoading.value = true;
    try {
        const res = await getMediaServers();
        const servers: StrmAPI.MediaServer[] = res.data || [];

        // 转换为Select选项，并根据服务器类型进行过滤
        const allServerOptions = servers.map(server => ({
            label: `${server.name} (${server.server_type})`,
            value: server.id,
            disabled: false,
            server
        }));

        // 根据服务器类型分离媒体服务器和下载服务器选项
        // 媒体服务器：类型为 "xiaoyahost"
        serverOptions.value = allServerOptions.filter(option =>
            (option.server as StrmAPI.MediaServer).server_type === 'xiaoyahost');

        // 下载服务器：类型为 "cd2host"
        downloadServerOptions.value = allServerOptions.filter(option =>
            (option.server as StrmAPI.MediaServer).server_type === 'cd2host');

        // 更新选项标签，去除冗余的类型标记
        serverOptions.value = serverOptions.value.map(option => ({
            ...option,
            label: (option.server as StrmAPI.MediaServer).name
        }));

        downloadServerOptions.value = downloadServerOptions.value.map(option => ({
            ...option,
            label: (option.server as StrmAPI.MediaServer).name
        }));

        // 从系统设置中获取默认值，确保默认服务器被选中
        if (systemSettings.value) {
            // 设置默认媒体服务器
            if (!formModel.value.serverId) {
                if (systemSettings.value.default_media_server_id) {
                    formModel.value.serverId = systemSettings.value.default_media_server_id;
                } else if (systemSettings.value.default_server_id) {
                    // 兼容旧版本
                    formModel.value.serverId = systemSettings.value.default_server_id;
                }
            }

            // 设置默认下载服务器
            if (!formModel.value.downloadServerId) {
                if (systemSettings.value.default_download_server_id) {
                    formModel.value.downloadServerId = systemSettings.value.default_download_server_id;
                } else if (systemSettings.value.default_server_id) {
                    // 兼容旧版本
                    formModel.value.downloadServerId = systemSettings.value.default_server_id;
                }
            }
        } else {
            // 如果没有系统设置，尝试使用标记为默认的服务器
            const defaultMediaServer = servers.find((s: StrmAPI.MediaServer) => s.is_default && (s.server_type === 'media' || s.server_type === 'both'));
            const defaultDownloadServer = servers.find((s: StrmAPI.MediaServer) => s.is_default && (s.server_type === 'download' || s.server_type === 'both'));

            if (!formModel.value.serverId && defaultMediaServer) {
                formModel.value.serverId = defaultMediaServer.id;
            }

            if (!formModel.value.downloadServerId && defaultDownloadServer) {
                formModel.value.downloadServerId = defaultDownloadServer.id;
            }
        }

        // 检查服务器可用性
        if (serverOptions.value.length === 0) {
            message.warning('没有找到xiaoyahost类型的媒体服务器');
        }

        if (downloadServerOptions.value.length === 0) {
            message.warning('没有找到cd2host类型的下载服务器');
        }
    } catch (error: any) {
        message.error(error.message || '获取媒体服务器失败');
    } finally {
        serversLoading.value = false;
    }
};

// 处理文件选择
const handleFileSelected = async (value: number | null) => {
    if (!value) {
        fileStats.value = null;
        return;
    }

    try {
        // 获取文件解析结果
        const res = await getParseResult(value);
        fileStats.value = res.data.stats;
    } catch (error: any) {
        message.error(error.message || '获取文件解析结果失败');
        selectedFileId.value = null;
    }
};

// 下一步
const handleNextStep = () => {
    if (currentStep.value < 2) {
        // 如果进入第二步（配置服务器），确保默认服务器已选中
        if (currentStep.value === 0) {
            // 确保已加载服务器选项
            if (!serverOptions.value.length || !downloadServerOptions.value.length) {
                fetchServers();
            }

            // 再次确认默认值已设置，只在未选择服务器时应用默认值
            if (systemSettings.value) {
                // 设置默认媒体服务器 - 只在当前未选择媒体服务器时设置默认值
                if (!formModel.value.serverId) {
                    if (systemSettings.value.default_media_server_id) {
                        formModel.value.serverId = systemSettings.value.default_media_server_id;
                    } else if (systemSettings.value.default_server_id) {
                        // 兼容旧版本
                        formModel.value.serverId = systemSettings.value.default_server_id;
                    }
                }

                // 设置默认下载服务器 - 只在当前未选择下载服务器时设置默认值
                if (!formModel.value.downloadServerId) {
                    if (systemSettings.value.default_download_server_id) {
                        formModel.value.downloadServerId = systemSettings.value.default_download_server_id;
                    } else if (systemSettings.value.default_server_id) {
                        // 兼容旧版本
                        formModel.value.downloadServerId = systemSettings.value.default_server_id;
                    }
                }
            }
        }

        currentStep.value++;
    }
};

// 更新任务信息的辅助函数
const updateTaskInfo = (data: any) => {
    if (!data) return;

    // 更新任务信息
    taskInfo.value = {
        ...taskInfo.value,
        ...data
    };

    // 优先使用后端返回的progress值
    if (taskInfo.value.total_files > 0 && (!data.progress || data.progress === 0)) {
        // 只有在后端未提供progress值时才计算
        taskInfo.value.progress = Math.min(
            100,
            Math.round((taskInfo.value.processed_files / taskInfo.value.total_files) * 100)
        );
    } else if (data.progress) {
        // 使用后端返回的progress值
        taskInfo.value.progress = data.progress;
    }

    // 更新最后更新时间
    lastUpdateTime.value = new Date();
};

// 获取任务状态
const pollTaskStatus = async () => {
    // 如果任务ID不存在或自动刷新被关闭，则不执行轮询
    if (!taskInfo.value.id || !autoRefresh.value) {
        // 如果自动刷新被关闭，确保标记轮询为停止状态
        taskPolling.value = true;
        return;
    }

    // 避免重复轮询
    if (taskPolling.value) {
        return;
    }

    taskPolling.value = true;
    try {
        const res = await getTaskStatus(taskInfo.value.id);

        if (!res.data) {
            message.error('获取任务状态失败，将在5秒后重试');
            // 清除之前的定时器
            if (refreshTimer) {
                clearTimeout(refreshTimer);
            }

            refreshTimer = window.setTimeout(() => {
                taskPolling.value = false;
                if (autoRefresh.value) pollTaskStatus();
            }, 5000);
            return;
        }

        // 保存上一次状态用于比较
        const prevStatus = taskInfo.value.status;
        const prevProcessed = taskInfo.value.processed_files;

        // 更新任务信息（包括进度值）
        updateTaskInfo(res.data);

        // 检查是否有进度变化
        const progressChanged = prevProcessed !== taskInfo.value.processed_files;

        // 如果任务还在运行，继续轮询
        if (taskInfo.value.status === 'running' || taskInfo.value.status === 'pending') {
            // 使用固定的1秒刷新间隔
            let pollInterval = refreshIntervalBase.value; // 固定为1000毫秒

            // 保持无更新检测功能
            if (!progressChanged) {
                noUpdateCounter.value++;
                if (noUpdateCounter.value >= MAX_NO_UPDATE_COUNT) {
                    console.warn(`连续${MAX_NO_UPDATE_COUNT}次未检测到进度更新，可能任务处理缓慢或出现问题`);
                    noUpdateCounter.value = 0;
                }
            } else {
                noUpdateCounter.value = 0;
            }

            // 清除之前的定时器
            if (refreshTimer) {
                clearTimeout(refreshTimer);
            }

            // 只有在自动刷新开启时才设置下一次轮询
            if (autoRefresh.value) {
                refreshTimer = window.setTimeout(() => {
                    taskPolling.value = false;
                    pollTaskStatus();
                }, pollInterval);
            } else {
                taskPolling.value = false;
            }
        } else {
            // 任务完成，停止轮询
            taskPolling.value = true;

            if (taskInfo.value.status === 'completed') {
                message.success('STRM文件生成完成');
                stepStatus.value = 'finish';
            } else if (taskInfo.value.status === 'failed') {
                message.error(taskInfo.value.error || 'STRM文件生成失败');
                stepStatus.value = 'error';
            } else if (taskInfo.value.status === 'canceled') {
                message.warning('STRM文件生成已取消');
                stepStatus.value = 'error';
            }
        }
    } catch (error: any) {
        console.error('获取任务状态错误:', error);
        message.error(error.message || '获取任务状态失败');

        // 错误后仍然继续轮询，但使用更长的间隔
        if (refreshTimer) {
            clearTimeout(refreshTimer);
        }

        if (autoRefresh.value) {
            refreshTimer = window.setTimeout(() => {
                taskPolling.value = false;
                pollTaskStatus();
            }, 5000);
        } else {
            taskPolling.value = false;
        }
    }
};

// 处理生成STRM文件
const handleGenerateStrm = async () => {
    if (!selectedFileId.value) {
        message.warning('请选择一个文件');
        return;
    }

    if (!formModel.value.serverId) {
        message.warning('请选择媒体服务器');
        return;
    }

    if (!formModel.value.downloadServerId) {
        message.warning('请选择下载服务器');
        return;
    }

    generating.value = true;
    let retryCount = 0;
    const maxRetries = 0; // 禁用重试功能，原为2

    const requestData = {
        record_id: selectedFileId.value,
        server_id: formModel.value.serverId,
        download_server_id: formModel.value.downloadServerId,
        name: formModel.value.name || undefined
    };

    async function attemptGenerateStrm() {
        try {
            const res = await generateStrm(requestData);

            if (!res || !res.data) {
                throw new Error('服务器响应异常，请稍后重试');
            }

            // 从返回数据中获取任务ID（同时检查task_id和id字段）
            const taskId = res.data.task_id || res.data.id;

            if (!taskId) {
                // 处理任务创建失败但API返回成功的情况
                const errorMsg = res.data.error || '创建任务失败，未获取到任务ID';
                throw new Error(errorMsg);
            }

            // 更新任务信息
            taskInfo.value = {
                id: taskId,
                name: res.data.name || '正在初始化...',
                status: res.data.status || 'pending',
                task_type: 'strm',
                total_files: 0, // 初始值设为0，稍后通过轮询获取实际值
                processed_files: 0,
                success_files: 0,
                failed_files: 0,
                progress: 0,
                output_dir: '',
                files: [],
                file_count: 0,
                resource_files_count: 0,
                strm_files_count: 0,
                strm_success: 0,
                strm_failed: 0,
                resource_success: 0,
                resource_failed: 0,
                video_files_count: 0
            };

            // 前进到下一步
            currentStep.value = 2;

            // 更新URL参数
            updateUrlParams();

            // 使用HTTP获取任务状态
            await getTaskStatusOnce();
            // 启动定时刷新，延迟5秒后开始轮询，避免重复请求
            taskPolling.value = false;
            setTimeout(() => {
                if (autoRefresh.value && (taskInfo.value.status === 'running' || taskInfo.value.status === 'pending')) {
                    pollTaskStatus();
                }
            }, 5000);

            message.success(res.data.message || '任务创建成功，开始生成STRM文件');
            return true;
        } catch (error: any) {
            if (retryCount < maxRetries) {
                retryCount++;
                message.warning(`请求失败，正在进行第${retryCount}次重试...`);
                await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒后重试
                return attemptGenerateStrm();
            }

            console.error('STRM生成错误:', error);
            message.error(error.message || 'STRM文件生成失败，请稍后重试');
            return false;
        }
    }

    try {
        await attemptGenerateStrm();
    } finally {
        generating.value = false;
    }
};

// 取消任务
const handleCancelTask = async () => {
    if (!taskInfo.value.id) return;

    try {
        await cancelTask(taskInfo.value.id);
        message.success('任务已取消');

        // 更新任务状态
        taskInfo.value.status = 'canceled';
        stepStatus.value = 'error';
    } catch (error: any) {
        message.error(error.message || '取消任务失败');
    }
};

// 跳转到任务管理页面
const goToTasksPage = () => {
    router.push('/strm/tasks');
};



// 获取状态文本
const getStatusText = (status: string) => {
    return STATUS_TEXT[status as keyof typeof STATUS_TEXT] || status;
};

// 获取进度条状态
const getProgressStatus = (status: string) => {
    if (status === 'completed') return 'success';
    if (status === 'failed' || status === 'canceled') return 'error';
    return 'info';
};

// 格式化日期时间，将ISO格式转换为更易读的格式
const formatDateTime = (dateTimeString: string) => {
    try {
        const date = new Date(dateTimeString);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
    } catch (error) {
        return dateTimeString;
    }
};

// 获取状态标签类型
const getStatusTagType = (status: string) => {
    switch (status) {
        case 'completed':
        case 'success':
            return 'success';
        case 'failed':
            return 'error';
        case 'canceled':
            return 'warning';
        case 'running':
            return 'info';
        case 'pending':
            return 'default';
        default:
            return 'default';
    }
};

// 获取STRM文件下载URL
const getStrmDownloadUrl = (taskId: number) => {
    return getStrmDownloadUrlApi(taskId);
};

// 添加一个单次获取任务状态的函数，不设置轮询
const getTaskStatusOnce = async () => {
    if (!taskInfo.value.id) return;

    try {
        const res = await getTaskStatus(taskInfo.value.id);

        if (!res.data) {
            console.error('获取任务状态失败');
            return;
        }

        // 更新任务信息
        updateTaskInfo(res.data);

        // 检查任务是否已结束
        if (res.data.status === 'completed' || res.data.status === 'failed' || res.data.status === 'canceled') {
            taskPolling.value = true; // 停止轮询
            // 更新任务完成状态
            if (res.data.status === 'completed') {
                message.success('STRM文件生成完成');
                stepStatus.value = 'finish';
            } else if (res.data.status === 'failed') {
                message.error(res.data.error || 'STRM文件生成失败');
                stepStatus.value = 'error';
            } else if (res.data.status === 'canceled') {
                message.warning('STRM文件生成已取消');
                stepStatus.value = 'error';
            }
        }
    } catch (error) {
        console.error('单次获取任务状态失败:', error);
    }
};

// 更新URL参数
const updateUrlParams = () => {
    // 更新URL参数，但不触发路由变化
    if (currentStep.value > 0) {
        const query = { ...route.query };
        query.step = currentStep.value.toString();

        if (taskInfo.value.id) {
            query.taskId = taskInfo.value.id.toString();
        }

        router.replace({ query });
    }
};

// 从URL参数恢复状态
const restoreState = async () => {
    // 检查URL参数
    const stepParam = route.query.step ? parseInt(route.query.step as string) : null;
    const taskIdParam = route.query.taskId ? parseInt(route.query.taskId as string) : null;

    // 如果URL中有任务ID和步骤参数，恢复状态
    if (taskIdParam && stepParam && stepParam > 0) {
        try {
            // 设置步骤
            currentStep.value = stepParam;

            // 恢复任务信息
            taskInfo.value.id = taskIdParam;

            // 获取任务详情
            await getTaskStatusOnce();

            // 如果任务仍在运行，启动轮询
            if (taskInfo.value.status === 'running' || taskInfo.value.status === 'pending') {
                taskPolling.value = false;
                pollTaskStatus();
            } else if (taskInfo.value.status === 'completed') {
                stepStatus.value = 'finish';
            } else if (taskInfo.value.status === 'failed' || taskInfo.value.status === 'canceled') {
                stepStatus.value = 'error';
            }

            return true;
        } catch (error) {
            console.error('从URL恢复状态失败:', error);
            message.error('恢复任务状态失败，将返回初始页面');
        }
    }

    return false;
};

// 组件挂载时获取数据
onMounted(async () => {
    // 尝试恢复状态
    const restored = await restoreState();

    // 如果没有恢复状态，则正常初始化
    if (!restored) {
        fetchFiles();

        // 先获取系统设置，然后获取服务器列表并设置默认值
        await fetchSystemSettings();
        await fetchServers();
    }
});

// 监听关键状态变化，更新URL参数
watch([currentStep, () => taskInfo.value.id], () => {
    updateUrlParams();
}, { deep: true });

// 清理资源的通用函数
const cleanupResources = () => {
    // 停止自动刷新
    autoRefresh.value = false;

    // 清除定时器
    if (refreshTimer) {
        clearTimeout(refreshTimer);
        refreshTimer = null;
    }

    // 停止轮询
    taskPolling.value = true;
};

// 页面路由离开时清理资源
onBeforeRouteLeave(() => {
    cleanupResources();
});

// 组件卸载时清理资源
onBeforeUnmount(() => {
    cleanupResources();
});

// 计算是否有成功文件
const hasSuccessFiles = computed(() => taskInfo.value.success_files > 0);

// 判断任务是否完成
const isTaskCompleted = computed(() =>
    ['completed', 'failed', 'canceled'].includes(taskInfo.value.status || '')
);

// 判断任务是否活跃（可以取消）
const isTaskActive = computed(() =>
    ['pending', 'running'].includes(taskInfo.value.status || '')
);

// 下载文件
const downloadFiles = () => {
    if (taskInfo.value.id) {
        const downloadUrl = getStrmDownloadUrlApi(taskInfo.value.id);
        window.open(downloadUrl, '_blank');
    }
};

// 跳转到任务管理页面
const goToHistory = () => {
    router.push('/strm/tasks');
};

// 手动刷新任务状态
const handleManualRefresh = async () => {
    if (!taskInfo.value.id || refreshing.value) return;

    refreshing.value = true;
    try {
        // 直接获取最新状态
        const res = await getTaskStatus(taskInfo.value.id);

        if (!res.data) {
            message.warning('获取任务状态失败');
            return;
        }

        // 更新任务信息
        updateTaskInfo(res.data);
        message.success('已刷新任务状态');

        // 根据任务状态决定后续操作
        if ((taskInfo.value.status === 'running' || taskInfo.value.status === 'pending')) {
            // 如果任务仍在进行中且开启了自动刷新，则确保轮询继续
            if (autoRefresh.value && !taskPolling.value) {
                message.info('重新启动状态更新');
                // 重置轮询计数器
                noUpdateCounter.value = 0;
                // 重新开始轮询
                pollTaskStatus();
            }
        } else {
            // 任务已完成，更新状态
            if (taskInfo.value.status === 'completed') {
                stepStatus.value = 'finish';
            } else if (taskInfo.value.status === 'failed' || taskInfo.value.status === 'canceled') {
                stepStatus.value = 'error';
            }
        }
    } catch (error: any) {
        message.error(error.message || '刷新状态失败');
    } finally {
        refreshing.value = false;
    }
};

// 切换自动刷新状态
const toggleAutoRefresh = (value: boolean) => {
    // 直接使用传入的值
    autoRefresh.value = value;

    if (autoRefresh.value) {
        message.info('已开启自动刷新');
        // 如果开启自动刷新且任务仍在进行中，立即开始轮询
        if ((taskInfo.value.status === 'running' || taskInfo.value.status === 'pending')) {
            // 清除之前的定时器
            if (refreshTimer) {
                clearTimeout(refreshTimer);
                refreshTimer = null;
            }
            // 重置轮询标志并立即开始轮询
            taskPolling.value = false;
            pollTaskStatus();
        }
    } else {
        message.info('已关闭自动刷新，您可以点击刷新按钮手动更新状态');
        // 清除现有定时器
        if (refreshTimer) {
            clearTimeout(refreshTimer);
            refreshTimer = null;
        }
    }
};
</script>

<style lang="scss" scoped>
.n-statistic {
    margin-right: 20px;
}

.step-content {
    min-height: 300px;
    padding: 8px 0;
    animation: fadeIn 0.3s ease-in-out;
}

.step-content-area {
    margin-top: 24px;
    padding: 0 8px;
}

// 添加开关的间距
.ml-8px {
    margin-left: 8px;
}
// 统计卡片样式
.stat-card {
    padding: 16px;
    border-radius: 4px;
    background-color: rgba(0, 0, 0, 0.02);
    border: 1px solid rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    &:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        transform: translateY(-2px);
    }

    .stat-label {
        font-size: 14px;
        color: var(--text-color-secondary);
        margin-bottom: 8px;
        text-align: center;
    }

    .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: var(--text-color-base);
        text-align: center;
    }
}

// 状态卡片样式
.status-card {
    padding: 16px;
    border-radius: 4px;
    background-color: rgba(0, 0, 0, 0.02);
    border: 1px solid rgba(0, 0, 0, 0.05);
    transition: all 0.3s ease;
    height: 100%;

    &:hover {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    }

    .status-header {
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 12px;
        color: var(--text-color-base);
        padding-bottom: 8px;
        border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    }

    .status-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }

    .status-item {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;

        &.success {
            .value {
                color: var(--success-color);
                font-weight: 600;
            }
        }

        &.error {
            .value {
                color: var(--error-color);
                font-weight: 600;
            }
        }

        .label {
            color: var(--text-color-secondary);
        }

        .value {
            font-weight: 500;
        }
    }
}

// 进度条样式优化
.progress-section {
    :deep(.n-progress) {
        &.n-progress--line {
            margin: 12px 0;
            position: relative;
            overflow: visible;
        }

        .n-progress-graph {
            transition: all 0.3s ease;
            z-index: 1;
        }

        .n-progress-graph__fill {
            box-shadow: 0 0 8px rgba(var(--primary-color), 0.3);
        }

        .n-progress-text {
            font-weight: 600;
            position: relative;
            z-index: 2;
        }
    }
}

// Fix for progress bar and status cards
.progress-bar {
    width: 100%;
    position: relative;
    overflow: hidden;
}

.task-header {
    z-index: 10;
    position: relative;
}

.stat-card, .status-card {
    z-index: 5;
    position: relative;
    background-color: var(--card-color, #fff);
}

// 操作区域样式
.action-section {
    padding: 8px 0;

    :deep(.n-button) {
        min-width: 120px;
        transition: all 0.3s ease;

        &:not(:disabled):hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
    }
}

// 分隔线样式
:deep(.n-divider) {
    margin: 24px 0 16px;

    .n-divider__title {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-color-secondary);
    }
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

// 卡片样式优化
:deep(.n-card) {
    transition: box-shadow 0.3s ease;

    &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
}

// 步骤指示器样式优化
:deep(.n-steps) {
    padding: 8px 0;
    margin-bottom: 24px;

    // 增强当前步骤的高亮效果
    .n-step--process {
        .n-step-indicator {
            background-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgb(var(--primary-color), 0.2);
            transition: all 0.3s ease;
            transform: scale(1.1);
        }

        .n-step-header {
            .n-step-title {
                color: rgb(var(--primary-color));
                font-weight: bold;
            }

            .n-step-description {
                color: rgb(var(--primary-color), 0.8);
            }
        }
    }
}

// 标签样式
:deep(.n-tag) {
    padding: 4px 8px;
    font-size: 12px;
}

// 响应式布局调整
@media (max-width: 1200px) {
    .stats-section {
        :deep(.n-grid) {
            grid-template-columns: repeat(2, 1fr) !important;
        }
    }
}

@media (max-width: 768px) {
    .step-content-area {
        padding: 0;
    }

    .status-stats {
        :deep(.n-grid) {
            grid-template-columns: repeat(1, 1fr) !important;
        }
    }

    .task-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;

        > div:nth-child(2) {
            width: 100%;
            display: flex;
            justify-content: flex-end;
        }
    }
}

// 按钮组样式
.flex.justify-center.gap-16px,
.flex.justify-between,
.flex.justify-end {
    margin-top: 20px;

    .n-button {
        min-width: 100px;
    }
}
</style>



