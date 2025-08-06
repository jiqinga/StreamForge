<template>
  <div>
    <n-card :bordered="false" class="h-full rounded-8px shadow-sm">
      <div class="flex flex-col space-y-4 mb-4">
        <div class="flex justify-between">
          <h2 class="text-xl font-bold">上传历史</h2>
          <n-button type="primary" @click="goToUpload">上传新文件</n-button>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <n-input v-model:value="historySearchValue" placeholder="搜索文件名..." clearable style="width: 200px"
            @keyup.enter="handleHistorySearch" />

          <n-date-picker v-model:value="dateRange" type="daterange" clearable style="width: 260px" placeholder="选择时间范围"
            :shortcuts="dateShortcuts" />

          <n-button type="primary" size="medium" style="width: 80px; height: 34px;" @click="handleHistorySearch">
            搜索
          </n-button>

          <n-button size="medium" style="height: 34px;" @click="clearFilters">
            清除筛选
          </n-button>
        </div>
      </div>

      <n-data-table :columns="columns" :data="historyData" :loading="loading" :pagination="{
        page: pagination.page,
        pageSize: pagination.pageSize,
        showSizePicker: true,
        pageSizes: [10, 20, 50, 100],
        itemCount: pagination.itemCount,
        prefix: ({ itemCount }) => `共 ${itemCount} 条`,
        showQuickJumper: true
      }" remote :row-key="row => row.id" @update:page="handlePageChange" @update:page-size="handlePageSizeChange" />
    </n-card>

    <!-- 解析结果对话框 -->
    <n-modal v-model:show="showResultModal" preset="card" title="文件解析结果" :bordered="false" size="huge"
      style="max-width: 900px;">
      <file-parse-result :record-id="currentRecord?.id || ''" :parse-result="parseResult" :record-info="currentRecord"
        :loading="resultLoading" @update:loading="resultLoading = $event"
        @file-page-change="handleFileParseResultPageChange" ref="fileParseResultRef" />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { DataTableColumns, PaginationProps } from 'naive-ui';
import {
  NButton,
  NCard,
  NDataTable,
  NDatePicker,
  NInput,
  NModal,
  NPopconfirm,
  NSpace,
  NTag,
  useMessage
} from 'naive-ui';
import FileParseResult from '@/components/custom/file-parse-result.vue';
import { deleteUploadRecord, getDownloadUrl, getParseResult, getUploadHistory } from '@/service/api/strm';
import { localStg } from '@/utils/storage';

defineOptions({
  name: 'StrmHistory'
});

const message = useMessage();
const loading = ref(false);
const historyData = ref<StrmAPI.UploadRecord[]>([]);

// 解析结果相关
const showResultModal = ref(false);
const resultLoading = ref(false);
const parseResult = ref<StrmAPI.ParseResult | null>(null);
const currentRecord = ref<StrmAPI.UploadRecord | null>(null); // 当前查看的记录
// 文件解析结果组件引用
const fileParseResultRef = ref<InstanceType<typeof FileParseResult> | null>(null);

// 分页配置
const pagination = reactive<PaginationProps>({
  page: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100],
  itemCount: 0,
  prefix: ({ itemCount }) => `共 ${itemCount} 条`,
  showQuickJumper: true
});

// 实用函数 - 加载所有数据（可选）
// 注意：仅在需要本地筛选时使用
const _fetchAllHistoryData = async () => {

};

// 处理文件解析结果分页变化
const handleFileParseResultPageChange = (params: { page: number; pageSize: number; fileType: string }) => {
  // 这里可以记录当前选择的文件类型和分页信息

};

// 历史记录搜索值
const historySearchValue = ref('');

// 日期范围
const dateRange = ref<[number, number] | null>(null);

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

// 原始历史数据
const originalHistoryData = ref<StrmAPI.UploadRecord[]>([]);
// 服务器端总记录数
const serverTotalCount = ref(0);
// 这些变量不再使用
// const allHistoryData = ref<StrmAPI.UploadRecord[]>([]);
// const hasLoadedAllData = ref(false);

// 获取路由器
const router = useRouter();

// 获取历史数据
const fetchHistory = async () => {
  loading.value = true;
  try {
    const { data } = await getUploadHistory({
      page: pagination.page,
      page_size: pagination.pageSize
    });
    if (data) {
      // 更新数据和分页信息
      historyData.value = data.records;
      originalHistoryData.value = data.records;

      // 重要：设置正确的总记录数，这决定了分页控件显示的页数
      pagination.itemCount = data.total;

      // 记录服务器返回的总数
      serverTotalCount.value = data.total;

    }
  } catch (error: any) {
    message.error(`获取历史记录失败: ${error.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
};

// 未来可以再次使用这个函数加载所有数据（注释掉以避免linter错误）
/*
const fetchAllHistoryData = async () => {
  // 此功能已被移除，因为我们使用共享组件和后端分页
};
*/

// 处理历史记录搜索
const handleHistorySearch = async () => {
  // 在前端进行简单搜索过滤（未来可以扩展为后端API搜索）
  // 重置分页到第一页
  pagination.page = 1;

  // 前端过滤
  if (historySearchValue.value || dateRange.value) {
    let filtered = [...originalHistoryData.value];

    // 按文件名过滤
    if (historySearchValue.value.trim()) {
      const searchText = historySearchValue.value.trim().toLowerCase();
      filtered = filtered.filter(record =>
        record.filename.toLowerCase().includes(searchText)
      );
    }

    // 按日期过滤
    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      const [startTime, endTime] = dateRange.value;
      filtered = filtered.filter(record => {
        const recordTime = new Date(record.create_time).getTime();
        return recordTime >= startTime && recordTime <= endTime;
      });
    }

    // 更新显示数据和计数
    historyData.value = filtered;
    // 重要：更新分页控件的总条目数，确保它显示正确的页数
    pagination.itemCount = filtered.length;
    message.info(`找到 ${filtered.length} 条匹配记录`);
  } else {
    // 如果没有筛选条件，重新加载服务器数据
    fetchHistory();
  }
};

// 清除筛选
const clearFilters = () => {
  historySearchValue.value = '';
  dateRange.value = null;
  historyData.value = originalHistoryData.value;
  pagination.itemCount = serverTotalCount.value;
  message.info('已清除筛选条件');
};

// 处理分页变化
const handlePageChange = (page: number) => {
  pagination.page = page;
  // 清除筛选条件
  historySearchValue.value = '';
  dateRange.value = null;
  // 重新加载数据
  fetchHistory();
};

// 处理每页数量变化
const handlePageSizeChange = (pageSize: number) => {
  pagination.pageSize = pageSize;
  pagination.page = 1; // 重置到第一页
  // 清除筛选条件
  historySearchValue.value = '';
  dateRange.value = null;
  // 重新加载数据
  fetchHistory();
};

// 删除记录操作
const deleteRecord = async (row: StrmAPI.UploadRecord) => {
  try {
    await deleteUploadRecord(row.id);
    message.success('记录已成功删除');
    fetchHistory(); // 刷新数据
  } catch (error: any) {
    message.error(`删除失败: ${error.message || '未知错误'}`);
  }
};

// 下载文件操作
const downloadFile = async (row: StrmAPI.UploadRecord) => {
  // 显示加载提示
  const loadingMsg = message.loading('正在准备下载...', {
    duration: 10000 // 10秒后自动关闭
  });

  try {
    // 获取认证令牌 - 使用Fast-Soy-Admin的存储工具localStg
    const token = localStg.get('token') || '';
    if (!token) {
      message.error('认证信息不存在，请重新登录');
      loadingMsg?.destroy(); // 关闭加载提示
      return;
    }

    // 构建下载URL，直接在URL中添加token参数
    const baseUrl = getDownloadUrl(row.id);
    const downloadUrl = `${baseUrl}?token=${encodeURIComponent(token)}`;

    // 方法1：使用fetch + blob方式下载（更加可靠但可能较慢）
    try {
      const response = await fetch(downloadUrl);

      if (!response.ok) {
        throw new Error(`下载失败: ${response.statusText}`);
      }

      // 获取文件名
      let filename = row.filename;
      const contentDisposition = response.headers.get('content-disposition');
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1];
        }
      }

      // 获取blob
      const blob = await response.blob();

      // 创建下载链接
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;

      // 触发下载
      document.body.appendChild(link);
      link.click();

      // 清理
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(link);
      }, 100);

      loadingMsg?.destroy();
      message.success('文件下载已开始');
    } catch (e) {
      // 如果fetch方法失败，尝试方法2
      console.error('Fetch下载失败，尝试直接打开方式:', e);

      // 方法2：直接在新窗口中打开下载链接
      window.open(downloadUrl, '_blank');

      loadingMsg?.destroy();
      message.success('已在新窗口打开下载链接');
    }
  } catch (error: any) {
    // 关闭加载提示
    loadingMsg?.destroy();
    message.error(`下载文件失败: ${error.message || '未知错误'}`);
  }
};

// 解析文件操作
const parseFile = async (row: StrmAPI.UploadRecord) => {
  try {
    // 对于已上传但未解析的文件进行解析
    loading.value = true;
    const { parseDirectoryTree } = await import('@/service/api/strm');
    await parseDirectoryTree({
      record_id: row.id
    });
    message.success('文件解析成功');
    fetchHistory(); // 刷新数据
  } catch (error: any) {
    message.error(`解析失败: ${error.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
};

// 查看解析结果
const viewParseResult = async (row: StrmAPI.UploadRecord) => {
  if (row.status !== 'parsed') {
    message.warning('该文件尚未解析，无法查看结果');
    return;
  }

  try {
    resultLoading.value = true;

    // 保存当前记录
    currentRecord.value = row;

    // 获取解析结果
    const { data } = await getParseResult(row.id, {
      page: 1,
      pageSize: 10
    });

    if (data) {
      // 更新解析结果
      parseResult.value = data;
    } else {
      message.error('获取解析结果失败: 响应数据为空');
      parseResult.value = null;
    }

    // 显示对话框
    showResultModal.value = true;
  } catch (error: any) {
    message.error(`获取解析结果失败: ${error.message || '未知错误'}`);
    showResultModal.value = false;
  } finally {
    resultLoading.value = false;
  }
};

// 定义处理函数引用
const handleDelete = (row: StrmAPI.UploadRecord) => deleteRecord(row);
const handleDownload = (row: StrmAPI.UploadRecord) => downloadFile(row);
const handleParse = (row: StrmAPI.UploadRecord) => parseFile(row);
const handleViewResult = (row: StrmAPI.UploadRecord) => viewParseResult(row);

// 基础列配置 - 所有列都居中对齐
const baseColumnConfig = {
  align: 'center'
};

// 表格列定义
const columns: DataTableColumns<StrmAPI.UploadRecord> = [
  { ...baseColumnConfig, title: 'ID', key: 'id', width: 80 },
  { ...baseColumnConfig, title: '文件名', key: 'filename', ellipsis: { tooltip: true } },
  {
    ...baseColumnConfig,
    title: '文件大小',
    key: 'filesize',
    render(row) {
      return `${(row.filesize / 1024 / 1024).toFixed(2)} MB`;
    }
  },
  {
    ...baseColumnConfig,
    title: '状态',
    key: 'status',
    render(row) {
      const statusMap: Record<string, string> = {
        'uploaded': '未解析',
        'parsing': '解析中',
        'parsed': '已解析',
        'failed': '解析失败'
      };

      // 定义状态对应的标签类型
      const typeMap: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
        'uploaded': 'warning',
        'parsing': 'info',
        'parsed': 'success',
        'failed': 'error'
      };

      // 定义状态对应的图标
      const iconMap: Record<string, string> = {
        'uploaded': '⏳',
        'parsing': '⚙️',
        'parsed': '✅',
        'failed': '❌'
      };

      return h(NTag, {
        type: typeMap[row.status] || 'default',
        size: 'medium',
        round: true
      }, {
        default: () => [
          // 添加图标和文本
          iconMap[row.status] || '',
          ' ',
          statusMap[row.status] || row.status
        ]
      });
    }
  },
  {
    ...baseColumnConfig,
    title: '上传时间',
    key: 'create_time',
    render(row) {
      return new Date(row.create_time).toLocaleString();
    }
  },
  {
    ...baseColumnConfig,
    title: '解析时间',
    key: 'parse_time',
    render(row) {
      return row.parse_time ? new Date(row.parse_time).toLocaleString() : '-';
    }
  },
  {
    ...baseColumnConfig,
    title: '操作',
    key: 'actions',
    render(row) {
      return h(NSpace, { justify: 'center' }, {
        default: () => [
          // 下载按钮
          h(NButton, {
            size: 'small',
            type: 'primary',
            onClick: () => handleDownload(row)
          }, { default: () => '下载' }),

          // 查看结果按钮 - 仅显示给已解析的文件
          row.status === 'parsed' ?
            h(NButton, {
              size: 'small',
              type: 'info',
              onClick: () => handleViewResult(row)
            }, { default: () => '查看结果' }) : null,

          // 解析按钮 - 仅显示在未解析的文件
          row.status === 'uploaded' || row.status === 'failed' ?
            h(NButton, {
              size: 'small',
              type: 'info',
              onClick: () => handleParse(row)
            }, { default: () => '解析' }) : null,

          // 删除按钮 - 使用确认对话框
          h(NPopconfirm, {
            onPositiveClick: () => handleDelete(row)
          }, {
            trigger: () => h(NButton, {
              size: 'small',
              type: 'error'
            }, { default: () => '删除' }),
            default: () => '确定要删除此记录吗？'
          })
        ]
      });
    }
  }
];

// 导航到上传页面
const goToUpload = () => {
  router.push('/strm/upload');
};

onMounted(() => {
  fetchHistory();
});
</script>

<style scoped>
.file-content-area {
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
}

/* 自定义对话框样式，确保它有足够的高度 */
:deep(.n-modal.n-modal--card-huge) {
  max-width: 80vw !important;
}

:deep(.n-modal-body) {
  padding: 16px;
  max-height: 80vh;
  overflow: auto;
}
</style>
