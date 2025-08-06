<template>
  <n-tag :type="tagType" size="medium" round>
    {{ iconText }} {{ statusText }}
  </n-tag>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NTag } from 'naive-ui';

const props = defineProps({
  status: {
    type: String,
    required: true
  },
  task: {
    type: Object,
    default: () => ({})
  },
  taskType: {
    type: String,
    default: 'strm' // 'strm' 或 'resource_download'
  }
});

// 计算实际状态，考虑资源文件下载情况
const actualStatus = computed(() => {
  const status = (props.status || '').toUpperCase();
  const taskType = props.taskType || (props.task?.task_type || 'strm');

  // 如果状态是COMPLETED或SUCCESS，检查是否有失败的文件
  if ((status === 'COMPLETED' || status === 'SUCCESS') && props.task) {
    if (taskType === 'strm') {
      const failedFiles = props.task.failed_files || 0;
      const resourceFailedFiles = props.task.resource_failed || 0;

      // 如果有失败的文件，判断为部分成功
      if (failedFiles > 0 || resourceFailedFiles > 0) {
        return 'PARTIAL_SUCCESS';
      }
    } else if (taskType === 'resource_download') {
      const failedFiles = props.task.failed_files || 0;

      // 对于资源下载任务，只检查下载失败的文件
      if (failedFiles > 0) {
        return 'PARTIAL_SUCCESS';
      }
    }
  }

  return status;
});

// 计算状态文本
const statusText = computed(() => {
  const status = actualStatus.value;
  const taskType = props.taskType || (props.task?.task_type || 'strm');

  const commonMap: Record<string, string> = {
    'PENDING': '等待中',
    'RUNNING': taskType === 'resource_download' ? '下载中' : '处理中',
    'CANCELED': '已取消',
    'FAILED': '失败'
  };

  const strmMap: Record<string, string> = {
    ...commonMap,
    'SUCCESS': '已完成',
    'COMPLETED': '已完成',
    'PARTIAL_SUCCESS': '部分成功'
  };

  const downloadMap: Record<string, string> = {
    ...commonMap,
    'SUCCESS': '下载完成',
    'COMPLETED': '下载完成',
    'PARTIAL_SUCCESS': '部分下载成功'
  };

  return (taskType === 'resource_download' ? downloadMap[status] : strmMap[status]) || status;
});

// 计算状态图标文本
const iconText = computed(() => {
  const status = actualStatus.value;
  const taskType = props.taskType || (props.task?.task_type || 'strm');

  const commonIcons: Record<string, string> = {
    'RUNNING': taskType === 'resource_download' ? '📥' : '⚙️',
    'PENDING': '⏳',
    'FAILED': '❌',
    'CANCELED': '🛑'
  };

  const strmIcons: Record<string, string> = {
    ...commonIcons,
    'SUCCESS': '✅',
    'COMPLETED': '✅',
    'PARTIAL_SUCCESS': '⚠️'
  };

  const downloadIcons: Record<string, string> = {
    ...commonIcons,
    'SUCCESS': '📁',
    'COMPLETED': '📁',
    'PARTIAL_SUCCESS': '⚠️'
  };

  return (taskType === 'resource_download' ? downloadIcons[status] : strmIcons[status]) || '❓';
});

// 计算Tag类型
const tagType = computed(() => {
  const status = actualStatus.value;
  switch (status) {
    case 'SUCCESS':
    case 'COMPLETED':
      return 'success';
    case 'PARTIAL_SUCCESS':
      return 'warning';
    case 'RUNNING':
      return 'info';
    case 'PENDING':
      return 'warning';
    case 'FAILED':
      return 'error';
    case 'CANCELED':
      return 'default';
    default:
      return 'default';
  }
});
</script>
