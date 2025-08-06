<template>
  <div class="segmented-progress-bar" :style="{ height: `${height}px` }">
    <n-tooltip trigger="hover" placement="top">
      <template #trigger>
        <div class="progress-track" :style="{ borderRadius: `${borderRadius}px` }">
          <!-- 成功部分 -->
          <div
            v-if="successPercentage > 0"
            class="progress-segment success"
            :style="{
              width: `${successPercentage}%`,
              borderRadius: getSuccessRadius(),
              background: successColor
            }"
          />
          <!-- 失败部分 -->
          <div
            v-if="failedPercentage > 0"
            class="progress-segment failed"
            :style="{
              width: `${failedPercentage}%`,
              borderRadius: getFailedRadius(),
              background: failedColor,
              left: `${successPercentage}%`
            }"
          />
          <!-- 处理中动画效果 -->
          <div
            v-if="processing && (successPercentage + failedPercentage) < 100"
            class="progress-processing"
            :style="{
              left: `${successPercentage + failedPercentage}%`,
              width: `${Math.min(10, 100 - successPercentage - failedPercentage)}%`
            }"
          />
        </div>
      </template>
      <div class="progress-tooltip">
        <div class="tooltip-title">{{ tooltipTitle }}</div>
        <div class="tooltip-content">
          <div class="tooltip-item success">
            <span class="tooltip-dot success-dot"></span>
            <span>成功: {{ successCount }} 个文件 ({{ successPercentage }}%)</span>
          </div>
          <div v-if="failedCount > 0" class="tooltip-item failed">
            <span class="tooltip-dot failed-dot"></span>
            <span>失败: {{ failedCount }} 个文件 ({{ failedPercentage }}%)</span>
          </div>
          <div v-if="pendingCount > 0" class="tooltip-item pending">
            <span class="tooltip-dot pending-dot"></span>
            <span>待处理: {{ pendingCount }} 个文件 ({{ pendingPercentage }}%)</span>
          </div>
          <div class="tooltip-summary">
            总计: {{ total }} 个文件
          </div>
        </div>
      </div>
    </n-tooltip>

    <!-- 进度标签 -->
    <div v-if="showLabels" class="progress-labels">
      <div v-if="successPercentage > 0" class="progress-label success">
        <span class="label-dot success-dot"></span>
        <span class="label-text">成功: {{ successCount }}/{{ total }}</span>
      </div>
      <div v-if="failedPercentage > 0" class="progress-label failed">
        <span class="label-dot failed-dot"></span>
        <span class="label-text">失败: {{ failedCount }}/{{ total }}</span>
      </div>
      <div v-if="pendingCount > 0" class="progress-label pending">
        <span class="label-dot pending-dot"></span>
        <span class="label-text">待处理: {{ pendingCount }}/{{ total }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NTooltip } from 'naive-ui';

interface Props {
  /** 成功文件数量 */
  successCount: number;
  /** 失败文件数量 */
  failedCount: number;
  /** 总文件数量 */
  total: number;
  /** 进度条高度 */
  height?: number;
  /** 边框圆角 */
  borderRadius?: number;
  /** 成功颜色 */
  successColor?: string;
  /** 失败颜色 */
  failedColor?: string;
  /** 是否显示处理中动画 */
  processing?: boolean;
  /** 是否显示标签 */
  showLabels?: boolean;
  /** Tooltip 标题 */
  tooltipTitle?: string;
}

const props = withDefaults(defineProps<Props>(), {
  height: 8,
  borderRadius: 4,
  successColor: '#52c41a',
  failedColor: '#f5222d',
  processing: false,
  showLabels: false,
  tooltipTitle: '文件处理进度'
});

// 计算百分比
const successPercentage = computed(() => {
  if (props.total === 0) return 0;
  return Math.round((props.successCount / props.total) * 100);
});

const failedPercentage = computed(() => {
  if (props.total === 0) return 0;
  return Math.round((props.failedCount / props.total) * 100);
});

const pendingCount = computed(() => {
  return Math.max(0, props.total - props.successCount - props.failedCount);
});

const pendingPercentage = computed(() => {
  if (props.total === 0) return 0;
  return Math.round((pendingCount.value / props.total) * 100);
});

// 计算边框圆角
const getSuccessRadius = () => {
  const radius = props.borderRadius;
  if (failedPercentage.value === 0) {
    // 只有成功部分，使用完整圆角
    return `${radius}px`;
  } else {
    // 有失败部分，左侧圆角，右侧直角
    return `${radius}px 0 0 ${radius}px`;
  }
};

const getFailedRadius = () => {
  const radius = props.borderRadius;
  if (successPercentage.value === 0) {
    // 只有失败部分，使用完整圆角
    return `${radius}px`;
  } else {
    // 有成功部分，右侧圆角，左侧直角
    return `0 ${radius}px ${radius}px 0`;
  }
};
</script>

<style scoped>
.segmented-progress-bar {
  width: 100%;
  position: relative;
}

.progress-track {
  width: 100%;
  height: 100%;
  background-color: #f0f0f0;
  position: relative;
  overflow: hidden;
}

.progress-segment {
  position: absolute;
  top: 0;
  height: 100%;
  transition: all 0.3s ease;
}

.progress-segment.success {
  z-index: 1;
}

.progress-segment.failed {
  z-index: 2;
}

.progress-processing {
  position: absolute;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(24, 144, 255, 0.3), transparent);
  animation: processing 2s infinite;
  z-index: 3;
}

@keyframes processing {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.progress-labels {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.progress-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.label-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.success-dot {
  background-color: #52c41a;
}

.failed-dot {
  background-color: #f5222d;
}

.pending-dot {
  background-color: #d9d9d9;
}

.label-text {
  color: var(--n-text-color-2);
  white-space: nowrap;
}

/* Tooltip 样式 */
.progress-tooltip {
  max-width: 280px;
}

.tooltip-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--n-text-color);
  margin-bottom: 8px;
  text-align: center;
}

.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tooltip-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--n-text-color-2);
}

.tooltip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tooltip-item .success-dot {
  background-color: #52c41a;
}

.tooltip-item .failed-dot {
  background-color: #f5222d;
}

.tooltip-item .pending-dot {
  background-color: #d9d9d9;
}

.tooltip-summary {
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--n-divider-color);
  font-size: 13px;
  font-weight: 500;
  color: var(--n-text-color);
  text-align: center;
}

.progress-track {
  cursor: pointer;
}
</style>
