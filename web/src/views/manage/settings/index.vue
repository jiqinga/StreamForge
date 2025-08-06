<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useMessage } from 'naive-ui';
import { getMediaServers, getSystemSettings, updateSystemSettings } from '@/service/api/strm';
import { $t } from '@/locales';
import ServerManagement from '@/components/custom/server-management.vue';

defineOptions({ name: 'ManageSystemSettings' });

const message = useMessage();

// 页面状态
const loading = ref(false);
const submitting = ref(false);
const activeTab = ref('basicSettings'); // 当前激活的选项卡: basicSettings, taskRecovery, logSettings 或 serverManagement
// 添加整个页面是否已加载数据的标记
const pageDataLoaded = ref(false);

// 记录错误信息
const errorInfo = ref({
  fileType: '', // 出错的文件类型 video, audio, image, subtitle, metadata
  extension: '', // 出错的扩展名，例如 .txt
  conflictType: '' // 冲突的文件类型
});

// 数据模型
const settings = ref({
  enablePathReplacement: false,
  replacementPath: '',
  downloadThreads: 0,
  outputDirectory: '',
  defaultMediaServerId: null as number | null,
  defaultDownloadServerId: null as number | null,
  videoFileTypes: '',
  audioFileTypes: '',
  imageFileTypes: '',
  subtitleFileTypes: '',
  metadataFileTypes: '',
  // 任务恢复配置
  enableTaskRecoveryPeriodicCheck: true,
  taskRecoveryCheckInterval: 1800,
  taskTimeoutHours: 2,
  heartbeatTimeoutMinutes: 10,
  activityCheckMinutes: 30,
  recentActivityMinutes: 5,
  // 重试配置
  failureRetryCount: 3,
  retryIntervalSeconds: 30,
  // 日志配置
  enableSqlLogging: false,
  logLevel: 'INFO',
  logsDirectory: 'app/logs',
  logRetentionDays: 30
});

// 计算属性：SQL日志开关是否应该被禁用
const isSqlLoggingDisabled = computed(() => {
  return settings.value.logLevel !== 'DEBUG';
});

// 监听日志级别变化，当不是DEBUG级别时自动禁用SQL日志
watch(() => settings.value.logLevel, (newLevel) => {
  if (newLevel !== 'DEBUG' && settings.value.enableSqlLogging) {
    settings.value.enableSqlLogging = false;
  }
});

// 服务器列表
const mediaServers = ref<Array<{ label: string; value: number }>>([]);
const downloadServers = ref<Array<{ label: string; value: number }>>([]);
// 所有服务器的原始数据，用于传递给服务器管理组件
const allServers = ref<Array<any>>([]);
// 标记服务器列表是否已加载
const serversLoaded = ref(false);

// 检查并确保默认服务器ID的有效性
function validateDefaultServerIds() {
  // 仅当服务器列表已加载时才进行验证
  if (!serversLoaded.value) return;

  if (settings.value.defaultMediaServerId &&
    !mediaServers.value.some(s => s.value === settings.value.defaultMediaServerId)) {
    console.warn(`默认媒体服务器ID ${settings.value.defaultMediaServerId} 不在有效的服务器列表中，可能已被删除`);
    settings.value.defaultMediaServerId = null;
  }

  if (settings.value.defaultDownloadServerId &&
    !downloadServers.value.some(s => s.value === settings.value.defaultDownloadServerId)) {
    console.warn(`默认下载服务器ID ${settings.value.defaultDownloadServerId} 不在有效的服务器列表中，可能已被删除`);
    settings.value.defaultDownloadServerId = null;
  }
}

// 文件类型标签数据
const videoFileTypeTags = computed({
  get: () => settings.value.videoFileTypes.split(',').filter(item => item.trim()),
  set: (val) => { settings.value.videoFileTypes = val.join(','); }
});

const audioFileTypeTags = computed({
  get: () => settings.value.audioFileTypes.split(',').filter(item => item.trim()),
  set: (val) => { settings.value.audioFileTypes = val.join(','); }
});

const imageFileTypeTags = computed({
  get: () => settings.value.imageFileTypes.split(',').filter(item => item.trim()),
  set: (val) => { settings.value.imageFileTypes = val.join(','); }
});

const subtitleFileTypeTags = computed({
  get: () => settings.value.subtitleFileTypes.split(',').filter(item => item.trim()),
  set: (val) => { settings.value.subtitleFileTypes = val.join(','); }
});

const metadataFileTypeTags = computed({
  get: () => settings.value.metadataFileTypes.split(',').filter(item => item.trim()),
  set: (val) => { settings.value.metadataFileTypes = val.join(','); }
});

// 格式化文件扩展名（确保以.开头）
function formatExtension(ext: string): string {
  const trimmed = ext.trim();
  if (!trimmed.startsWith('.') && trimmed !== '') {
    return `.${trimmed}`;
  }
  return trimmed;
}

// 验证文件扩展名是否有效
function validateExtension(ext: string): boolean {
  // 允许空字符串
  if (!ext) return true;
  // 扩展名应该以点开头，后面跟1-10个字母或数字
  const regex = /^\.[a-zA-Z0-9]{1,10}$/;
  return regex.test(ext);
}

// 标签添加前的验证
function beforeAddTag(tag: string, tagType: string): boolean | string {
  const formatted = formatExtension(tag);

  // 验证格式
  if (!validateExtension(formatted)) {
    message.warning('无效的文件扩展名格式');
    return false;
  }

  // 检查当前类型中是否有重复
  const existingTags = getTagsRefByType(tagType).value;
  const hasDuplicate = existingTags.some(t => t.toLowerCase() === formatted.toLowerCase());
  if (hasDuplicate) {
    message.warning('该扩展名已存在');
    return false;
  }

  // 不再检查其他类型中是否有重复，由后端进行验证

  return formatted;
}

// 根据类型获取对应的标签引用
function getTagsRefByType(type: string): typeof videoFileTypeTags {
  switch (type) {
    case 'video': return videoFileTypeTags;
    case 'audio': return audioFileTypeTags;
    case 'image': return imageFileTypeTags;
    case 'subtitle': return subtitleFileTypeTags;
    case 'metadata': return metadataFileTypeTags;
    default: return videoFileTypeTags;
  }
}

// 获取不同文件类型的标签样式
function getTagType(tagType: string): 'success' | 'info' | 'warning' | 'error' | 'default' | 'primary' {
  switch (tagType) {
    case 'video': return 'success';
    case 'audio': return 'info';
    case 'image': return 'warning';
    case 'subtitle': return 'error';
    case 'metadata': return 'primary';
    default: return 'default';
  }
}

// 获取系统设置
async function fetchSettings() {
  try {
    loading.value = true;
    const res = await getSystemSettings();
    if (res.data) {
      settings.value = {
        enablePathReplacement: res.data.enable_path_replacement ?? false,
        replacementPath: res.data.replacement_path ?? '',
        downloadThreads: res.data.download_threads ?? 1,
        outputDirectory: res.data.output_directory ?? '',
        defaultMediaServerId: res.data.default_media_server_id ?? null,
        defaultDownloadServerId: res.data.default_download_server_id ?? null,
        videoFileTypes: res.data.video_file_types ?? '',
        audioFileTypes: res.data.audio_file_types ?? '',
        imageFileTypes: res.data.image_file_types ?? '',
        subtitleFileTypes: res.data.subtitle_file_types ?? '',
        metadataFileTypes: res.data.metadata_file_types ?? '',
        // 任务恢复配置
        enableTaskRecoveryPeriodicCheck: res.data.enable_task_recovery_periodic_check ?? true,
        taskRecoveryCheckInterval: res.data.task_recovery_check_interval ?? 1800,
        taskTimeoutHours: res.data.task_timeout_hours ?? 2,
        heartbeatTimeoutMinutes: res.data.heartbeat_timeout_minutes ?? 10,
        activityCheckMinutes: res.data.activity_check_minutes ?? 30,
        recentActivityMinutes: res.data.recent_activity_minutes ?? 5,
        // 重试配置
        failureRetryCount: res.data.failure_retry_count ?? 3,
        retryIntervalSeconds: res.data.retry_interval_seconds ?? 30,
        // 日志配置
        enableSqlLogging: Boolean(res.data.enable_sql_logging),
        logLevel: res.data.log_level ?? 'INFO',
        logsDirectory: res.data.logs_directory ?? 'app/logs',
        logRetentionDays: res.data.log_retention_days ?? 30
      };

      // 如果服务器列表已加载，验证默认服务器ID的有效性
      if (serversLoaded.value) {
        validateDefaultServerIds();
      }
    }
  } catch (error: any) {
    message.error(error.message || $t('strm.settings.saveFail'));
    console.error('获取系统设置失败:', error);
  } finally {
    loading.value = false;
  }
}

// 获取服务器列表
async function fetchServers() {
  if (serversLoaded.value) {
    return; // 如果已加载过，则不重复加载
  }

  try {
    // 获取所有服务器
    const allRes = await getMediaServers();

    if (allRes.data && Array.isArray(allRes.data)) {
      // 保存原始服务器数据
      allServers.value = allRes.data;

      // 过滤出媒体服务器（xiaoyahost类型）
      mediaServers.value = allRes.data
        .filter(server => server.server_type === 'xiaoyahost')
        .map(server => ({
          label: server.name,
          value: server.id
        }));

      // 过滤出下载服务器（cd2host类型）
      downloadServers.value = allRes.data
        .filter(server => server.server_type === 'cd2host')
        .map(server => ({
          label: server.name,
          value: server.id
        }));

      serversLoaded.value = true; // 标记为已加载

      // 当服务器列表加载完成后，验证默认服务器ID的有效性
      validateDefaultServerIds();
    }
  } catch (error: any) {
    message.error(error.message || $t('strm.settings.saveFail'));
  }
}

// 加载所有页面数据（只在页面初始化时调用一次）
async function loadAllPageData() {
  if (pageDataLoaded.value) return; // 如果已加载过，不重复加载

  loading.value = true;
  try {
    // 并行加载设置和服务器数据
    await Promise.all([fetchSettings(), fetchServers()]);
    pageDataLoaded.value = true; // 标记页面数据已加载完成
  } finally {
    loading.value = false;
  }
}

// 保存设置
async function saveSettings() {
  // 重置错误信息
  errorInfo.value = { fileType: '', extension: '', conflictType: '' };

  submitting.value = true;

  try {
    const requestData = {
      enable_path_replacement: settings.value.enablePathReplacement,
      replacement_path: settings.value.replacementPath,
      download_threads: settings.value.downloadThreads,
      output_directory: settings.value.outputDirectory,
      default_media_server_id: settings.value.defaultMediaServerId,
      default_download_server_id: settings.value.defaultDownloadServerId,
      video_file_types: settings.value.videoFileTypes,
      audio_file_types: settings.value.audioFileTypes,
      image_file_types: settings.value.imageFileTypes,
      subtitle_file_types: settings.value.subtitleFileTypes,
      metadata_file_types: settings.value.metadataFileTypes,
      // 任务恢复配置
      enable_task_recovery_periodic_check: settings.value.enableTaskRecoveryPeriodicCheck,
      task_recovery_check_interval: settings.value.taskRecoveryCheckInterval,
      task_timeout_hours: settings.value.taskTimeoutHours,
      heartbeat_timeout_minutes: settings.value.heartbeatTimeoutMinutes,
      activity_check_minutes: settings.value.activityCheckMinutes,
      recent_activity_minutes: settings.value.recentActivityMinutes,
      // 重试配置
      failure_retry_count: settings.value.failureRetryCount,
      retry_interval_seconds: settings.value.retryIntervalSeconds,
      // 日志配置
      enable_sql_logging: settings.value.enableSqlLogging,
      log_level: settings.value.logLevel,
      logs_directory: settings.value.logsDirectory,
      log_retention_days: settings.value.logRetentionDays
    };

    // 使用项目统一的API请求方法
    const response = await updateSystemSettings(requestData);

    // 检查响应是否有错误
    if (response.error) {
      // 如果有错误，提取错误信息并处理，然后返回
      const errorMsg = response.error.response?.data?.msg || '';

      if (errorMsg.includes('文件类型设置有误') || errorMsg.includes('扩展名')) {
        handleFileTypeError(errorMsg);
      }

      // 重要：无论什么错误，保存失败后重新加载服务器数据以保持UI与服务器数据一致
      await fetchSettings();

      return; // 有错误时直接返回，不继续执行
    }

    // 如果没有错误，显示成功消息
    message.success($t('strm.settings.saveSuccess'));

    // 重新加载设置数据
    await fetchSettings();
  } catch {
    // 这个catch块不会显示错误消息，因为所有HTTP错误都会被响应对象的error属性捕获
    // 或者被全局拦截器处理

    // 保存失败后也重新加载数据，确保UI状态与服务器一致
    await fetchSettings();
  } finally {
    submitting.value = false;
  }
}

// 处理文件类型错误
function handleFileTypeError(errorMsg: string): void {
  // 解析出错的文件类型和扩展名
  let extensionMatch = errorMsg.match(/扩展名\s+(\.\w+)\s+在\s+(\w+)\s+类型中重复/);
  if (extensionMatch && extensionMatch.length >= 3) {
    const extension = extensionMatch[1]; // 例如 .txt
    const fileTypeText = extensionMatch[2]; // 例如 元数据

    // 将中文文件类型名称转换为英文标识符
    let fileType = '';
    if (fileTypeText === '视频') fileType = 'video';
    else if (fileTypeText === '音频') fileType = 'audio';
    else if (fileTypeText === '图片') fileType = 'image';
    else if (fileTypeText === '字幕') fileType = 'subtitle';
    else if (fileTypeText === '元数据') fileType = 'metadata';

    // 保存错误信息
    errorInfo.value = { fileType, extension, conflictType: '' };
  } else {
    // 尝试匹配不同类型的错误：同一个文件后缀不能属于不同的文件类型
    extensionMatch = errorMsg.match(/扩展名\s+(\.\w+)\s+在\s+(\w+)\s+和\s+(\w+)\s+类型中均存在/);
    if (extensionMatch && extensionMatch.length >= 4) {
      const extension = extensionMatch[1]; // 例如 .svg
      const fileTypeText1 = extensionMatch[2]; // 例如 图片
      const fileTypeText2 = extensionMatch[3]; // 例如 字幕

      // 确定主要冲突类型和次要冲突类型
      let fileType = '';
      let conflictType = '';

      // 转换第一个文件类型
      if (fileTypeText1 === '视频') fileType = 'video';
      else if (fileTypeText1 === '音频') fileType = 'audio';
      else if (fileTypeText1 === '图片') fileType = 'image';
      else if (fileTypeText1 === '字幕') fileType = 'subtitle';
      else if (fileTypeText1 === '元数据') fileType = 'metadata';

      // 转换第二个文件类型
      if (fileTypeText2 === '视频') conflictType = 'video';
      else if (fileTypeText2 === '音频') conflictType = 'audio';
      else if (fileTypeText2 === '图片') conflictType = 'image';
      else if (fileTypeText2 === '字幕') conflictType = 'subtitle';
      else if (fileTypeText2 === '元数据') conflictType = 'metadata';

      // 保存错误信息
      errorInfo.value = { fileType, extension, conflictType };
    }
  }

  // 确保在基本设置标签页
  activeTab.value = 'basicSettings';

  // 等待DOM更新后滚动到出错的文件类型区域
  setTimeout(() => {
    const fileTypeLabel = document.querySelector(`[data-filetype="${errorInfo.value.fileType}"]`);
    if (fileTypeLabel) {
      fileTypeLabel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 100);
}

// 检查标签是否有错误
function isTagInError(tagType: string, tagValue: string): boolean {
  return (errorInfo.value.fileType === tagType && errorInfo.value.extension === tagValue) ||
    (errorInfo.value.conflictType === tagType && errorInfo.value.extension === tagValue);
}

// 切换标签页 - 现在只需要切换标签页，不需要加载数据
function handleTabChange(name: string) {
  activeTab.value = name;
}

// 服务器变更时刷新列表
async function handleServersUpdate() {
  // 重新加载服务器列表
  serversLoaded.value = false;
  fetchServers().then(() => {
    // 检查默认服务器ID的有效性
    validateDefaultServerIds();
  });
}

// 初始化时加载所有数据
onMounted(async () => {
  // 一次性加载所有页面数据
  await loadAllPageData();
});
</script>

<template>
  <n-card :title="$t('strm.settings.title')" :bordered="false">
    <n-tabs v-model:value="activeTab" type="line" animated @update:value="handleTabChange">
      <!-- 基本设置选项卡 -->
      <n-tab-pane name="basicSettings" :tab="$t('strm.settings.basicSettings')">
        <n-spin :show="loading">
          <n-form label-placement="left" label-width="auto" require-mark-placement="right-hanging"
            :disabled="submitting" class="pt-20px">

            <!-- 默认下载服务器 -->
            <n-form-item :label="$t('strm.settings.defaultDownloadServer')">
              <n-select v-model:value="settings.defaultDownloadServerId" :options="downloadServers"
                :placeholder="$t('strm.settings.defaultDownloadServerPlaceholder')" clearable />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.defaultDownloadServerHelp')
                }}</span>
              </template>
            </n-form-item>

            <!-- 默认媒体服务器 -->
            <n-form-item :label="$t('strm.settings.defaultMediaServer')">
              <n-select v-model:value="settings.defaultMediaServerId" :options="mediaServers"
                :placeholder="$t('strm.settings.defaultMediaServerPlaceholder')" clearable />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.defaultMediaServerHelp')
                }}</span>
              </template>
            </n-form-item>

            <!-- 路径替换开关 -->
            <n-form-item :label="$t('strm.settings.enablePathReplacement')">
              <n-switch v-model:value="settings.enablePathReplacement" />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.enablePathReplacementHelp')
                }}</span>
              </template>
            </n-form-item>

            <!-- 路径替换值，只在开启时显示 -->
            <n-form-item :label="$t('strm.settings.replacementPath')" v-show="settings.enablePathReplacement">
              <n-input v-model:value="settings.replacementPath"
                :placeholder="$t('strm.settings.replacementPathPlaceholder')" />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.replacementPathHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 下载线程数 -->
            <n-form-item :label="$t('strm.settings.downloadThreads')">
              <n-input-number v-model:value="settings.downloadThreads" :min="1" :max="20" />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.downloadThreadsHelp')
                }}</span>
              </template>
            </n-form-item>

            <!-- 输出目录 -->
            <n-form-item :label="$t('strm.settings.outputDirectory')">
              <n-input v-model:value="settings.outputDirectory"
                :placeholder="$t('strm.settings.outputDirectoryPlaceholder')" />
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.outputDirectoryHelp')
                }}</span>
              </template>
            </n-form-item>

            <!-- 文件类型分隔线 -->
            <n-divider>{{ $t('strm.settings.fileTypesSettings') }}</n-divider>

            <!-- 视频文件类型 -->
            <n-form-item :label="$t('strm.settings.videoFileTypes')" data-filetype="video">
              <n-dynamic-tags v-model:value="videoFileTypeTags" :type="getTagType('video')" :input-props="{
                placeholder: $t('strm.settings.addExtensionPlaceholder')
              }" :add-button-props="{
                dashed: true,
                round: true
              }" :max="20" :before-add-tag="(tag: string) => beforeAddTag(tag, 'video')">
                <template #tag="{ tag, handleClose }">
                  <n-tag :type="getTagType('video')" closable @close="handleClose"
                    :style="isTagInError('video', tag) ? { backgroundColor: '#fff2f0', borderColor: '#ff4d4f', color: '#ff4d4f' } : {}">
                    {{ tag }}
                  </n-tag>
                </template>
              </n-dynamic-tags>
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.fileTypesHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 音频文件类型 -->
            <n-form-item :label="$t('strm.settings.audioFileTypes')" data-filetype="audio">
              <n-dynamic-tags v-model:value="audioFileTypeTags" :type="getTagType('audio')" :input-props="{
                placeholder: $t('strm.settings.addExtensionPlaceholder')
              }" :add-button-props="{
                dashed: true,
                round: true
              }" :max="20" :before-add-tag="(tag: string) => beforeAddTag(tag, 'audio')">
                <template #tag="{ tag, handleClose }">
                  <n-tag :type="getTagType('audio')" closable @close="handleClose"
                    :style="isTagInError('audio', tag) ? { backgroundColor: '#fff2f0', borderColor: '#ff4d4f', color: '#ff4d4f' } : {}">
                    {{ tag }}
                  </n-tag>
                </template>
              </n-dynamic-tags>
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.fileTypesHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 图片文件类型 -->
            <n-form-item :label="$t('strm.settings.imageFileTypes')" data-filetype="image">
              <n-dynamic-tags v-model:value="imageFileTypeTags" :type="getTagType('image')" :input-props="{
                placeholder: $t('strm.settings.addExtensionPlaceholder')
              }" :add-button-props="{
                dashed: true,
                round: true
              }" :max="20" :before-add-tag="(tag: string) => beforeAddTag(tag, 'image')">
                <template #tag="{ tag, handleClose }">
                  <n-tag :type="getTagType('image')" closable @close="handleClose"
                    :style="isTagInError('image', tag) ? { backgroundColor: '#fff2f0', borderColor: '#ff4d4f', color: '#ff4d4f' } : {}">
                    {{ tag }}
                  </n-tag>
                </template>
              </n-dynamic-tags>
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.fileTypesHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 字幕文件类型 -->
            <n-form-item :label="$t('strm.settings.subtitleFileTypes')" data-filetype="subtitle">
              <n-dynamic-tags v-model:value="subtitleFileTypeTags" :type="getTagType('subtitle')" :input-props="{
                placeholder: $t('strm.settings.addExtensionPlaceholder')
              }" :add-button-props="{
                dashed: true,
                round: true
              }" :max="20" :before-add-tag="(tag: string) => beforeAddTag(tag, 'subtitle')">
                <template #tag="{ tag, handleClose }">
                  <n-tag :type="getTagType('subtitle')" closable @close="handleClose"
                    :style="isTagInError('subtitle', tag) ? { backgroundColor: '#fff2f0', borderColor: '#ff4d4f', color: '#ff4d4f' } : {}">
                    {{ tag }}
                  </n-tag>
                </template>
              </n-dynamic-tags>
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.fileTypesHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 元数据文件类型 -->
            <n-form-item :label="$t('strm.settings.metadataFileTypes')" data-filetype="metadata">
              <n-dynamic-tags v-model:value="metadataFileTypeTags" :type="getTagType('metadata')" :input-props="{
                placeholder: $t('strm.settings.addExtensionPlaceholder')
              }" :add-button-props="{
                dashed: true,
                round: true
              }" :max="20" :before-add-tag="(tag: string) => beforeAddTag(tag, 'metadata')">
                <template #tag="{ tag, handleClose }">
                  <n-tag :type="getTagType('metadata')" closable @close="handleClose"
                    :style="isTagInError('metadata', tag) ? { backgroundColor: '#fff2f0', borderColor: '#ff4d4f', color: '#ff4d4f' } : {}">
                    {{ tag }}
                  </n-tag>
                </template>
              </n-dynamic-tags>
              <template #help>
                <span class="text-xs text-gray-400">{{ $t('strm.settings.fileTypesHelp') }}</span>
              </template>
            </n-form-item>

            <!-- 保存按钮 -->
            <n-form-item>
              <n-button type="primary" :loading="submitting" @click="saveSettings">{{
                $t('strm.settings.save') }}</n-button>
            </n-form-item>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- 任务恢复设置选项卡 -->
      <n-tab-pane name="taskRecovery" :tab="$t('strm.settings.taskRecoverySettings')">
        <n-spin :show="loading">
          <n-form label-placement="left" label-width="auto" require-mark-placement="right-hanging"
            :disabled="submitting" class="pt-20px">

            <!-- 定期检查开关 -->
            <n-form-item label="启用定期检查">
              <n-switch v-model:value="settings.enableTaskRecoveryPeriodicCheck">
                <template #checked>启用</template>
                <template #unchecked>禁用</template>
              </n-switch>
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                启用后系统会定期检查异常任务状态并自动修复
              </n-text>
            </n-form-item>

            <!-- 检查间隔 -->
            <n-form-item label="检查间隔（秒）">
              <n-input-number
                v-model:value="settings.taskRecoveryCheckInterval"
                :min="300"
                :max="7200"
                :step="300"
                placeholder="检查间隔时间"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                建议设置为 1800 秒（30分钟），范围：300-7200 秒
              </n-text>
            </n-form-item>

            <!-- 任务超时时间 -->
            <n-form-item label="任务超时时间（小时）">
              <n-input-number
                v-model:value="settings.taskTimeoutHours"
                :min="1"
                :max="24"
                placeholder="任务超时时间"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                超过此时间的运行中任务将被标记为失败，建议设置为 2 小时
              </n-text>
            </n-form-item>

            <!-- 心跳超时时间 -->
            <n-form-item label="心跳超时时间（分钟）">
              <n-input-number
                v-model:value="settings.heartbeatTimeoutMinutes"
                :min="1"
                :max="60"
                placeholder="心跳超时时间"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                任务心跳超时时间，建议设置为 10 分钟
              </n-text>
            </n-form-item>

            <!-- 活动检测窗口 -->
            <n-form-item label="活动检测窗口（分钟）">
              <n-input-number
                v-model:value="settings.activityCheckMinutes"
                :min="10"
                :max="120"
                placeholder="活动检测窗口"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                任务运行超过此时间后开始检查是否为僵尸任务。用于检测程序重启或崩溃后遗留的无效任务，建议 30-60 分钟
              </n-text>
            </n-form-item>

            <!-- 最近活动窗口 -->
            <n-form-item label="最近活动窗口（分钟）">
              <n-input-number
                v-model:value="settings.recentActivityMinutes"
                :min="1"
                :max="30"
                placeholder="最近活动窗口"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                检查此时间范围内是否有下载进度更新。如无更新则判定为僵尸任务并自动清理，建议 5-10 分钟
              </n-text>
            </n-form-item>

            <!-- 失败重试次数 -->
            <n-form-item label="失败重试次数">
              <n-input-number
                v-model:value="settings.failureRetryCount"
                :min="0"
                :max="10"
                placeholder="失败重试次数"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                STRM生成和资源下载失败时的重试次数，设置为0表示不重试，建议设置为 3 次
              </n-text>
            </n-form-item>

            <!-- 重试间隔时间 -->
            <n-form-item label="重试间隔时间（秒）">
              <n-input-number
                v-model:value="settings.retryIntervalSeconds"
                :min="5"
                :max="300"
                placeholder="重试间隔时间"
                style="width: 200px"
              />
              <n-text depth="3" style="margin-left: 12px; font-size: 12px;">
                任务失败后等待多长时间再次重试，建议设置为 30 秒，范围 5-300 秒
              </n-text>
            </n-form-item>



            <n-divider />

            <div class="flex justify-center">
              <n-button type="primary" :loading="submitting" @click="saveSettings">
                {{ $t('strm.settings.save') }}
              </n-button>
            </div>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- 日志配置选项卡 -->
      <n-tab-pane name="logSettings" :tab="$t('strm.settings.logSettings')">
        <n-spin :show="loading">
          <n-form label-placement="left" label-width="auto" require-mark-placement="right-hanging"
            :disabled="submitting" class="pt-20px">

            <!-- SQL日志开关 -->
            <n-form-item :label="$t('strm.settings.enableSqlLogging')">
              <div class="flex items-center space-x-3">
                <n-switch v-model:value="settings.enableSqlLogging" :disabled="isSqlLoggingDisabled">
                  <template #checked>启用</template>
                  <template #unchecked>禁用</template>
                </n-switch>
                <n-tag v-if="isSqlLoggingDisabled" type="warning" size="small">
                  需要DEBUG级别
                </n-tag>
              </div>
              <template #help>
                <div class="text-xs text-gray-400">
                  <p>{{ $t('strm.settings.enableSqlLoggingHelp') }}</p>
                  <div class="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-yellow-800">
                    <p class="font-medium">⚠️ 重要说明：</p>
                    <ul class="mt-1 space-y-1 text-xs">
                      <li>• <strong>仅在DEBUG模式下可用</strong>：SQL日志只能在日志级别为DEBUG时启用</li>
                      <li>• <strong>性能影响</strong>：启用后会记录所有数据库查询，可能影响系统性能</li>
                      <li>• <strong>日志量大</strong>：会产生大量日志输出，建议仅在调试时使用</li>
                      <li>• <strong>敏感信息</strong>：SQL日志可能包含敏感数据，请注意安全</li>
                      <li>• <strong>生产环境</strong>：不建议在生产环境中长期启用</li>
                    </ul>
                  </div>
                </div>
              </template>
            </n-form-item>



            <!-- 日志级别 -->
            <n-form-item :label="$t('strm.settings.logLevel')">
              <n-select v-model:value="settings.logLevel" :options="[
                { label: 'DEBUG', value: 'DEBUG' },
                { label: 'INFO', value: 'INFO' },
                { label: 'WARNING', value: 'WARNING' },
                { label: 'ERROR', value: 'ERROR' }
              ]" style="width: 200px" />
              <template #help>
                <div class="text-xs text-gray-400">
                  <p>{{ $t('strm.settings.logLevelHelp') }}</p>
                  <div class="mt-2 space-y-1">
                    <p><strong>DEBUG</strong>：记录所有日志信息，包括详细的调试信息和SQL查询（开发调试用）</p>
                    <p><strong>INFO</strong>：记录一般信息、警告和错误（推荐用于生产环境）</p>
                    <p><strong>WARNING</strong>：仅记录警告和错误信息</p>
                    <p><strong>ERROR</strong>：仅记录错误信息</p>
                  </div>
                </div>
              </template>
            </n-form-item>

            <!-- 日志存放目录 -->
            <n-form-item label="日志存放目录">
              <n-input v-model:value="settings.logsDirectory" placeholder="app/logs" />
              <template #help>
                <div class="text-xs text-gray-400">
                  <p>设置日志文件的存放目录。支持相对路径（相对于项目根目录）和绝对路径。</p>
                  <div class="mt-2 space-y-1">
                    <p><strong>默认目录</strong>：app/logs</p>
                    <p><strong>相对路径示例</strong>：app/logs、logs、data/logs</p>
                    <p><strong>绝对路径示例</strong>：/var/log/fast-soy-admin、D:\logs</p>
                  </div>
                  <div class="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-blue-800">
                    <p class="font-medium">💡 提示：</p>
                    <ul class="mt-1 space-y-1 text-xs">
                      <li>• 系统会自动创建不存在的目录</li>
                      <li>• 保存前会验证目录的写入权限</li>
                      <li>• 配置变更后立即生效，无需重启</li>
                      <li>• 现有日志文件不会移动，只影响新生成的日志</li>
                    </ul>
                  </div>
                </div>
              </template>
            </n-form-item>

            <!-- 日志保留天数 -->
            <n-form-item :label="$t('strm.settings.logRetentionDays')">
              <n-input-number v-model:value="settings.logRetentionDays" :min="1" :max="365" style="width: 200px" />
              <template #help>
                <div class="text-xs text-gray-400">
                  <p>{{ $t('strm.settings.logRetentionDaysHelp') }}</p>
                  <div class="mt-2 space-y-1">
                    <p><strong>默认值</strong>：30天</p>
                    <p><strong>取值范围</strong>：1-365天</p>
                    <p><strong>说明</strong>：超过指定天数的日志文件将被自动清理</p>
                  </div>
                  <div class="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-blue-800">
                    <p class="font-medium">💡 提示：</p>
                    <ul class="mt-1 space-y-1 text-xs">
                      <li>• 日志清理任务会在每天凌晨自动执行</li>
                      <li>• 设置较短的保留期可以节省磁盘空间</li>
                      <li>• 设置较长的保留期有利于问题追踪和分析</li>
                      <li>• 建议根据磁盘空间和业务需求合理设置</li>
                    </ul>
                  </div>
                </div>
              </template>
            </n-form-item>

            <n-divider />

            <div class="flex justify-center">
              <n-button type="primary" :loading="submitting" @click="saveSettings">
                {{ $t('strm.settings.save') }}
              </n-button>
            </div>
          </n-form>
        </n-spin>
      </n-tab-pane>

      <!-- 服务器管理选项卡 -->
      <n-tab-pane name="serverManagement" :tab="$t('strm.settings.serverManagement')">
        <server-management :auto-load="false" :external-servers="allServers" @update:servers="handleServersUpdate" />
      </n-tab-pane>
    </n-tabs>
  </n-card>
</template>

<style scoped>
.pt-20px {
  padding-top: 20px;
}
</style>
