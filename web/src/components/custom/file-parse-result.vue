<template>
    <div class="file-parse-result">
        <n-spin :show="loading">
            <div v-if="parseResult">
                <!-- 文件信息 -->
                <n-descriptions v-if="showInfo" label-placement="left" bordered>
                    <n-descriptions-item label="文件名">{{ parseResult.file_name }}</n-descriptions-item>
                    <n-descriptions-item label="总文件数">{{ parseResult.total_files }}</n-descriptions-item>
                    <n-descriptions-item label="解析时间" v-if="recordInfo && recordInfo.parse_time">
                        {{ new Date(recordInfo.parse_time).toLocaleString() }}
                    </n-descriptions-item>
                </n-descriptions>

                <!-- 统计信息 -->
                <div :class="{ 'mt-4': showInfo }">
                    <h3 class="mb-2">文件统计</h3>
                    <n-grid :cols="7" :x-gap="8">
                        <n-grid-item>
                            <n-statistic label="总文件" :value="parseResult.stats.total" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="视频" :value="parseResult.stats.video" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="音频" :value="parseResult.stats.audio" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="图片" :value="parseResult.stats.image" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="字幕" :value="parseResult.stats.subtitle" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="元数据" :value="parseResult.stats.metadata" />
                        </n-grid-item>
                        <n-grid-item>
                            <n-statistic label="其它" :value="parseResult.stats.other" />
                        </n-grid-item>
                    </n-grid>
                </div>

                <!-- 文件列表 -->
                <div class="mt-4">
                    <h3 class="mb-2">文件列表</h3>

                    <!-- 调整布局，使用两行排列 -->
                    <div class="mb-4">
                        <!-- 第一行：文件类型过滤 -->
                        <div class="mb-3">
                            <n-radio-group v-model:value="fileTypeFilter" size="small"
                                @update:value="handleFileTypeChange">
                                <n-radio-button value="all">全部 ({{ parseResult.stats.total || 0 }})</n-radio-button>
                                <n-radio-button value="video">视频 ({{ parseResult.stats.video || 0 }})</n-radio-button>
                                <n-radio-button value="audio">音频 ({{ parseResult.stats.audio || 0 }})</n-radio-button>
                                <n-radio-button value="image">图片 ({{ parseResult.stats.image || 0 }})</n-radio-button>
                                <n-radio-button value="subtitle">字幕 ({{ parseResult.stats.subtitle || 0
                                }})</n-radio-button>
                                <n-radio-button value="metadata">元数据 ({{ parseResult.stats.metadata || 0
                                }})</n-radio-button>
                                <n-radio-button value="other">其它 ({{ parseResult.stats.other || 0 }})</n-radio-button>
                            </n-radio-group>
                            <div v-if="parseResult.pagination" class="text-xs text-gray-500 mt-1">
                                当前显示: {{ parsedFiles.length }}条，总计: {{ parseResult.pagination.total }}条
                            </div>
                        </div>

                        <!-- 第二行：视图切换与搜索 -->
                        <div class="flex justify-end items-center">
                            <n-input v-model:value="fileSearchValue" placeholder="搜索文件名..." clearable
                                style="width: 200px" class="mr-2" @keyup.enter="handleSearch" />
                            <n-button type="primary" class="mr-2" size="medium" style="width: 80px; height: 34px;"
                                @click="handleSearch">
                                搜索
                            </n-button>
                            <n-button-group size="medium">
                                <n-button :type="viewMode === 'table' ? 'primary' : 'default'"
                                    @click="handleViewModeChange('table')" style="width: 50px; height: 34px;">
                                    表格
                                </n-button>
                                <n-button :type="viewMode === 'tree' ? 'primary' : 'default'"
                                    @click="handleViewModeChange('tree')" style="width: 50px; height: 34px;">
                                    树形
                                </n-button>
                            </n-button-group>
                        </div>
                    </div>

                    <!-- 文件内容区域：添加固定高度和边框 -->
                    <div class="file-content-area border border-gray-200 rounded-md"
                        style="height: 400px; max-height: 60vh; overflow: auto;">
                        <!-- 表格视图 -->
                        <n-data-table v-if="viewMode === 'table'" :columns="fileColumns" :data="parsedFiles"
                            size="small" :pagination="filePagination" :loading="loading" remote
                            :row-key="row => row.file_name + row.path" @update:page="handleFilePageChange"
                            @update:page-size="handleFilePageSizeChange" class="w-full" />

                        <!-- 树形视图 -->
                        <div v-else class="h-full">
                            <file-tree-view :record-id="recordId" :file-type-filter="fileTypeFilter"
                                :search-value="fileSearchValue" :root-directories="rootDirectories"
                                :root-files="rootFiles" class="p-2 h-full" ref="fileTreeViewRef" />
                        </div>
                    </div>
                </div>
            </div>
            <div v-else class="empty-state">
                <n-empty description="暂无解析结果" />
                <p class="mt-2 text-secondary-text">请选择文件并解析后查看</p>
            </div>
        </n-spin>
    </div>
</template>

<script setup lang="ts">
import { computed, h, ref, watch, type PropType } from 'vue';
import { NButton, NButtonGroup, NDataTable, NDescriptions, NDescriptionsItem, NEmpty, NGrid, NGridItem, NInput, NRadioButton, NRadioGroup, NSpin, NStatistic, useMessage, type DataTableColumns, type PaginationProps } from 'naive-ui';
import FileTreeView from '@/components/custom/file-tree-view.vue';
import { getDirectoryContent, getParseResult, searchFiles } from '@/service/api/strm';

defineOptions({
    name: 'FileParseResult'
});

const props = defineProps({
    recordId: {
        type: [String, Number],
        required: true
    },
    parseResult: {
        type: Object as PropType<StrmAPI.ParseResult | null>,
        default: null
    },
    recordInfo: {
        type: Object as PropType<StrmAPI.UploadRecord | null>,
        default: null
    },
    loading: {
        type: Boolean,
        default: false
    },
    showInfo: {
        type: Boolean,
        default: true
    }
});

const emit = defineEmits(['update:loading', 'file-page-change']);

const message = useMessage();

// 文件类型过滤
const fileTypeFilter = ref('all');
// 视图模式：表格或树形
const viewMode = ref<'table' | 'tree'>('table');
// 文件搜索关键词
const fileSearchValue = ref('');
// 解析后的文件数据（当前显示）
const parsedFiles = ref<StrmAPI.ParsedFile[]>([]);
// 树形视图组件引用
const fileTreeViewRef = ref<InstanceType<typeof FileTreeView> | null>(null);
// 根目录下的内容（用于树形视图懒加载）
const rootDirectories = ref<string[]>([]);
const rootFiles = ref<StrmAPI.ParsedFile[]>([]);

// 文件列表分页配置 - 使用服务端分页
const filePagination = ref({
    page: 1,
    pageSize: 10,
    showSizePicker: true,
    pageSizes: [10, 20, 50, 100],
    itemCount: 0,
    prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 条`,
    showQuickJumper: true,
});

// 数据表格配置
const fileColumns: DataTableColumns<StrmAPI.ParsedFile> = [
    {
        title: '文件名',
        key: 'file_name',
        ellipsis: {
            tooltip: true
        }
    },
    {
        title: '类型',
        key: 'file_type',
        width: 80,
        render(row) {
            const typeMap = {
                video: '视频',
                audio: '音频',
                image: '图片',
                subtitle: '字幕',
                metadata: '元数据',
                other: '其他'
            };
            return typeMap[row.file_type as keyof typeof typeMap] || row.file_type;
        }
    },
    {
        title: '扩展名',
        key: 'extension',
        width: 80
    },
    {
        title: '目录',
        key: 'directory',
        ellipsis: {
            tooltip: true
        }
    }
];

// 对外暴露方法
defineExpose({
    refreshData,
    handleSearch
});

// 当parseResult改变时，更新文件列表和分页信息
watch(() => props.parseResult, (newValue) => {
    if (newValue) {
        parsedFiles.value = newValue.parsed_files || [];

        // 更新分页信息
        if (newValue.pagination) {
            filePagination.value.itemCount = newValue.pagination.total;
        } else {
            // 兼容旧版API响应，使用stats中的数据
            filePagination.value.itemCount = fileTypeFilter.value === 'all'
                ? (newValue.stats?.total || 0)
                : (newValue.stats?.[fileTypeFilter.value as keyof typeof newValue.stats] || 0);
        }

        // 如果是树形视图，需要初始化根目录和文件
        if (viewMode.value === 'tree') {
            loadTreeData();
        }
    } else {
        parsedFiles.value = [];
        filePagination.value.itemCount = 0;
    }
}, { immediate: true });

// 加载树形视图数据
async function loadTreeData() {
    if (!props.recordId) return;

    try {
        emit('update:loading', true);

        const { data } = await getDirectoryContent(props.recordId, {
            directoryPath: '/',
            fileType: fileTypeFilter.value
        });

        if (data) {
            // 从items数组中分离目录和文件
            const subdirectories: string[] = [];
            const files: StrmAPI.ParsedFile[] = [];

            // 处理返回的items数组
            (data.items || []).forEach(item => {
                const fileName = item.file_name;

                // 辅助函数: 判断是否为文件（通过扩展名）
                const hasExtension = (name: string) => {
                    // 移除可能的尾部斜杠
                    const cleanName = name.endsWith('/') ? name.slice(0, -1) : name;
                    const parts = cleanName.split('.');
                    return parts.length > 1 && parts[parts.length - 1].length > 0;
                };

                // 若is_directory已明确为true则为目录; 否则通过检查文件名来判断
                const isFile = item.is_directory === false ||
                    (item.is_directory === undefined && hasExtension(fileName));

                if (isFile) {
                    // 如果是文件，添加到文件数组
                    if (item.file_name.endsWith('/')) {
                        // 修复尾部斜杠的问题
                        item.file_name = item.file_name.slice(0, -1);
                    }
                    files.push(item as StrmAPI.ParsedFile);
                } else {
                    // 如果是目录，提取目录名（去除路径前缀）
                    subdirectories.push(fileName);
                }
            });

            rootDirectories.value = subdirectories;
            rootFiles.value = files;
        }
    } catch (error: any) {
        message.error(`加载目录内容失败: ${error.message || '未知错误'}`);
    } finally {
        emit('update:loading', false);
    }
}

// 文件类型变化处理
function handleFileTypeChange() {
    // 重置分页
    filePagination.value.page = 1;
    refreshData();
}

// 视图模式变化处理
function handleViewModeChange(mode: 'table' | 'tree') {
    viewMode.value = mode;
    refreshData();
}

// 文件分页处理函数
function handleFilePageChange(page: number) {
    filePagination.value.page = page;
    refreshData();
}

// 文件分页大小变化处理函数
function handleFilePageSizeChange(pageSize: number) {
    filePagination.value.pageSize = pageSize;
    filePagination.value.page = 1; // 重置到第一页
    refreshData();
}

// 搜索处理函数
function handleSearch() {
    const searchValue = fileSearchValue.value.trim();

    if (!props.recordId) {
        message.error('无法执行搜索，记录ID无效');
        return;
    }

    // 如果是表格视图，需要调用后端API进行搜索
    if (viewMode.value === 'table') {
        message.info(`正在搜索: "${searchValue}"...`);
        emit('update:loading', true);

        searchFiles(props.recordId, searchValue, {
            fileType: fileTypeFilter.value,
            ignoreCase: true
        })
            .then(response => {
                if (response?.data?.matches) {
                    parsedFiles.value = response.data.matches;
                    // 更新分页信息，使用搜索结果的总数
                    filePagination.value.itemCount = response.data.total_matches;
                    // 重置到第一页
                    filePagination.value.page = 1;
                    message.success(`找到 ${response.data.total_matches} 个匹配项`);
                } else {
                    parsedFiles.value = [];
                    // 没有匹配项时，设置总数为0
                    filePagination.value.itemCount = 0;
                    filePagination.value.page = 1;
                    message.info('未找到匹配项');
                }

                // 通知父组件分页信息变化
                emit('file-page-change', {
                    page: filePagination.value.page,
                    pageSize: filePagination.value.pageSize,
                    fileType: fileTypeFilter.value
                });
            })
            .catch(error => {
                message.error(`搜索失败: ${error.message || '未知错误'}`);
            })
            .finally(() => {
                emit('update:loading', false);
            });
    }
    // 如果是树形视图，调用树形视图组件的performSearch方法
    else if (viewMode.value === 'tree') {
        if (fileTreeViewRef.value) {
            fileTreeViewRef.value.performSearch(searchValue);
        } else {
            message.error('树形视图组件未加载，无法执行搜索');
        }
    }
}

// 刷新数据
async function refreshData() {
    if (!props.recordId) return;

    try {
        emit('update:loading', true);

        if (viewMode.value === 'tree') {
            // 树形视图模式 - 加载根目录内容
            await loadTreeData();
        } else {
            // 表格视图模式 - 使用分页加载
            const { data } = await getParseResult(props.recordId, {
                fileType: fileTypeFilter.value,
                page: filePagination.value.page,
                pageSize: filePagination.value.pageSize
            });

            if (data) {
                parsedFiles.value = data.parsed_files || [];

                // 使用后端返回的分页信息更新分页控件
                if (data.pagination) {
                    filePagination.value.itemCount = data.pagination.total;
                } else {
                    // 兼容旧版API响应，使用stats中的数据
                    filePagination.value.itemCount = fileTypeFilter.value === 'all'
                        ? (data.stats?.total || 0)
                        : (data.stats?.[fileTypeFilter.value as keyof typeof data.stats] || 0);
                }

                // 通知父组件分页信息变化
                emit('file-page-change', {
                    page: filePagination.value.page,
                    pageSize: filePagination.value.pageSize,
                    fileType: fileTypeFilter.value
                });
            }
        }
    } catch (error: any) {
        message.error(`加载解析结果失败: ${error.message || '未知错误'}`);
    } finally {
        emit('update:loading', false);
    }
}
</script>

<style scoped>
.file-parse-result {
    width: 100%;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    margin: 1rem 0;
    min-height: 200px;
    text-align: center;
}

.empty-state p {
    margin-top: 0.5rem;
    color: var(--n-text-color-disabled);
    font-size: 0.875rem;
}
</style>
