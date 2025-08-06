import { ref, onUnmounted, nextTick } from 'vue';
import { useMessage } from 'naive-ui';

interface LogStreamOptions {
  taskId: number;
  onLogUpdate?: (logs: string[]) => void;
  onError?: (error: Error) => void;
  interval?: number; // 轮询间隔，毫秒
  maxRetries?: number; // 最大重试次数
}

interface LogStreamState {
  isStreaming: boolean;
  logs: string[];
  error: string | null;
  lastUpdateTime: Date | null;
}

export function useLogStream() {
  const message = useMessage();

  const state = ref<LogStreamState>({
    isStreaming: false,
    logs: [],
    error: null,
    lastUpdateTime: null
  });

  let streamTimer: NodeJS.Timeout | null = null;
  let retryCount = 0;
  let currentOptions: LogStreamOptions | null = null;

  // 开始日志流
  const startStream = async (options: LogStreamOptions) => {
    if (state.value.isStreaming) {
      stopStream();
    }

    currentOptions = options;
    state.value.isStreaming = true;
    state.value.error = null;
    retryCount = 0;

    await fetchLogs();
    scheduleNextFetch();
  };

  // 停止日志流
  const stopStream = () => {
    if (streamTimer) {
      clearTimeout(streamTimer);
      streamTimer = null;
    }

    state.value.isStreaming = false;
    currentOptions = null;
    retryCount = 0;
  };

  // 获取日志数据
  const fetchLogs = async () => {
    if (!currentOptions) return;

    try {
      // 这里应该调用实际的API
      const { getTaskLogs } = await import('@/service/api/strm');

      const { data } = await getTaskLogs(currentOptions.taskId, {
        // 可以添加时间戳参数来获取增量日志
        // since: state.value.lastUpdateTime?.toISOString()
      });

      if (data && data.raw_content) {
        const newLogs = data.raw_content.split('\n')
          .filter((line: string) => line.trim() !== '')
          .map((line: string) => line);

        // 如果是增量更新，合并日志
        if (state.value.lastUpdateTime) {
          state.value.logs = [...state.value.logs, ...newLogs];
        } else {
          state.value.logs = newLogs;
        }

        state.value.lastUpdateTime = new Date();
        state.value.error = null;
        retryCount = 0;

        // 触发回调
        if (currentOptions.onLogUpdate) {
          currentOptions.onLogUpdate(state.value.logs);
        }
      }
    } catch (error: any) {
      console.error('获取日志失败:', error);

      state.value.error = error.message || '获取日志失败';
      retryCount++;

      // 触发错误回调
      if (currentOptions.onError) {
        currentOptions.onError(error);
      }

      // 如果重试次数超过限制，停止流
      const maxRetries = currentOptions.maxRetries || 3;
      if (retryCount >= maxRetries) {
        message.error(`日志获取失败，已重试 ${maxRetries} 次，停止自动更新`);
        stopStream();
        return;
      }
    }
  };

  // 调度下次获取
  const scheduleNextFetch = () => {
    if (!state.value.isStreaming || !currentOptions) return;

    const interval = currentOptions.interval || 5000; // 默认5秒

    streamTimer = setTimeout(async () => {
      if (state.value.isStreaming) {
        await fetchLogs();
        scheduleNextFetch();
      }
    }, interval);
  };

  // 手动刷新
  const refresh = async () => {
    if (!currentOptions) return;

    // 重置最后更新时间以获取完整日志
    state.value.lastUpdateTime = null;
    await fetchLogs();
  };

  // 清空日志
  const clearLogs = () => {
    state.value.logs = [];
    state.value.lastUpdateTime = null;
  };

  // 组件卸载时清理
  onUnmounted(() => {
    stopStream();
  });

  return {
    state: state.value,
    startStream,
    stopStream,
    refresh,
    clearLogs,
    isStreaming: () => state.value.isStreaming
  };
}

// 日志过滤工具函数
export function filterLogs(logs: string[], filters: {
  search?: string;
  level?: string;
  exclude?: string;
  regex?: string;
  timeRange?: [Date, Date];
}) {
  let filtered = [...logs];

  // 搜索过滤
  if (filters.search) {
    const searchTerm = filters.search.toLowerCase();
    filtered = filtered.filter(log =>
      log.toLowerCase().includes(searchTerm)
    );
  }

  // 级别过滤
  if (filters.level) {
    filtered = filtered.filter(log =>
      log.includes(`[${filters.level!.toUpperCase()}]`)
    );
  }

  // 排除过滤
  if (filters.exclude) {
    const excludeTerm = filters.exclude.toLowerCase();
    filtered = filtered.filter(log =>
      !log.toLowerCase().includes(excludeTerm)
    );
  }

  // 正则表达式过滤
  if (filters.regex) {
    try {
      const regex = new RegExp(filters.regex, 'i');
      filtered = filtered.filter(log => regex.test(log));
    } catch (error) {
      console.warn('无效的正则表达式:', filters.regex);
    }
  }

  // 时间范围过滤
  if (filters.timeRange) {
    const [startTime, endTime] = filters.timeRange;
    filtered = filtered.filter(log => {
      // 从日志中提取时间戳
      const timestampMatch = log.match(/\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]/);
      if (timestampMatch) {
        const logTime = new Date(timestampMatch[1]);
        return logTime >= startTime && logTime <= endTime;
      }
      return true; // 如果无法提取时间戳，保留日志
    });
  }

  return filtered;
}

// 日志统计工具函数
export function analyzeLogStats(logs: string[]) {
  const stats = {
    total: logs.length,
    info: 0,
    warning: 0,
    error: 0,
    debug: 0,
    other: 0
  };

  logs.forEach(log => {
    if (log.includes('[INFO]')) {
      stats.info++;
    } else if (log.includes('[WARNING]')) {
      stats.warning++;
    } else if (log.includes('[ERROR]')) {
      stats.error++;
    } else if (log.includes('[DEBUG]')) {
      stats.debug++;
    } else {
      stats.other++;
    }
  });

  return stats;
}

// 日志导出工具函数
export function exportLogsToFile(logs: string[], filename: string, options?: {
  includeHeader?: boolean;
  taskName?: string;
  filters?: any;
}) {
  const { includeHeader = true, taskName, filters } = options || {};

  let content = '';

  if (includeHeader) {
    content += `# ${taskName || '任务'} 日志导出\n`;
    content += `# 导出时间: ${new Date().toLocaleString()}\n`;
    content += `# 总日志数: ${logs.length}\n`;

    if (filters) {
      content += `# 应用的过滤器:\n`;
      if (filters.search) content += `#   搜索: ${filters.search}\n`;
      if (filters.level) content += `#   级别: ${filters.level}\n`;
      if (filters.logType) content += `#   类型: ${filters.logType}\n`;
      if (filters.timeRange) content += `#   时间范围: ${new Date(filters.timeRange[0]).toLocaleString()} - ${new Date(filters.timeRange[1]).toLocaleString()}\n`;
    }

    content += '\n';
  }

  content += logs.join('\n');

  // 创建并下载文件
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}
