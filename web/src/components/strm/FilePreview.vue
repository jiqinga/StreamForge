<template>
  <div class="file-preview">
    <!-- 预览内容 -->
    <div class="preview-content">
      <n-spin :show="loading">
        <!-- 错误状态 -->
        <div v-if="previewData?.preview_type === 'error'" class="preview-error">
          <n-result status="error" title="预览失败" :description="previewData.error">
            <template #icon>
              <n-icon size="48" color="#ff6b6b">
                <Icon icon="mdi:alert-circle" />
              </n-icon>
            </template>
          </n-result>
        </div>

        <!-- STRM文件预览 -->
        <div v-else-if="previewData?.preview_type === 'strm'" class="preview-strm">
          <div class="strm-header">
            <div class="strm-title">
              <n-icon size="24" color="#52c41a">
                <Icon icon="mdi:play-circle" />
              </n-icon>
              <span class="title-text">视频流媒体链接</span>
            </div>
            <div class="strm-meta">
              <n-tag type="success" size="small">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:check-circle" />
                  </n-icon>
                </template>
                STRM文件
              </n-tag>
            </div>
          </div>

          <div class="strm-content">
            <!-- 视频链接展示 -->
            <div class="video-link-section">
              <div class="section-title">
                <n-icon size="16">
                  <Icon icon="mdi:link-variant" />
                </n-icon>
                <span>视频链接</span>
              </div>

              <!-- 解码后的链接（可读性更好） -->
              <div class="link-container" v-if="previewData.decoded_content">
                <div class="link-label">解码后链接（可读）：</div>
                <div class="link-display">
                  <n-input
                    :value="previewData.decoded_content"
                    readonly
                    placeholder="解码后的视频链接"
                    class="link-input decoded-link"
                  />
                </div>
              </div>

              <!-- 原始编码链接 -->
              <div class="link-container">
                <div class="link-label">原始链接（编码）：</div>
                <div class="link-display">
                  <n-input
                    :value="previewData.content"
                    readonly
                    placeholder="原始视频链接"
                    class="link-input"
                  />
                </div>
                <div class="link-actions">
                  <n-button type="primary" @click="copyToClipboard(previewData.content)">
                    <template #icon>
                      <n-icon>
                        <Icon icon="mdi:content-copy" />
                      </n-icon>
                    </template>
                    复制原始链接
                  </n-button>
                  <n-button
                    v-if="previewData.decoded_content"
                    type="success"
                    @click="copyToClipboard(previewData.decoded_content)"
                  >
                    <template #icon>
                      <n-icon>
                        <Icon icon="mdi:content-copy" />
                      </n-icon>
                    </template>
                    复制解码链接
                  </n-button>
                  <n-button type="info" @click="toggleVideoPreview">
                    <template #icon>
                      <n-icon>
                        <Icon :icon="showVideoPlayer ? 'mdi:eye-off' : 'mdi:play'" />
                      </n-icon>
                    </template>
                    {{ showVideoPlayer ? '隐藏预览' : '预览视频' }}
                  </n-button>
                  <n-button type="warning" @click="testVideoLink(previewData.content)">
                    <template #icon>
                      <n-icon>
                        <Icon icon="mdi:play-network" />
                      </n-icon>
                    </template>
                    测试链接
                  </n-button>
                </div>
              </div>
            </div>

            <!-- 视频预览提示 -->
            <div class="video-preview-hint">
              <n-alert type="info" title="预览提示">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:lightbulb" />
                  </n-icon>
                </template>
                <div class="hint-content">
                  <p>• 点击"预览视频"可在当前页面直接播放视频</p>
                  <p>• 点击"测试链接"可检查链接的可访问性</p>
                  <p>• 如果视频无法播放，可能是格式不支持或网络问题</p>
                  <p>• 建议使用专业的媒体播放器（如VLC、PotPlayer等）播放完整视频</p>
                </div>
              </n-alert>
            </div>
          </div>
        </div>

        <!-- 文本文件预览 -->
        <div v-else-if="previewData?.preview_type === 'text'" class="preview-text">
          <div class="text-header">
            <div class="text-title">
              <n-icon size="20" color="#1890ff">
                <Icon :icon="getTextFileIcon()" />
              </n-icon>
              <span class="title-text">{{ getTextFileTitle() }}</span>
            </div>
            <div class="text-meta">
              <n-tag type="info" size="small">
                {{ getFileExtension().toUpperCase() }}文件
              </n-tag>
              <span class="content-length">{{ previewData.content?.length || 0 }} 字符</span>
            </div>
          </div>

          <div class="text-content">
            <div class="text-viewer">
              <n-input
                :value="previewData.content"
                type="textarea"
                readonly
                :autosize="{ minRows: 15, maxRows: 25 }"
                placeholder="文件内容"
                class="content-textarea"
              />
            </div>
            <div class="text-actions">
              <n-button type="primary" @click="copyToClipboard(previewData.content)">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:content-copy" />
                  </n-icon>
                </template>
                复制全部内容
              </n-button>
              <n-button type="info" @click="downloadTextFile()">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:download" />
                  </n-icon>
                </template>
                下载文件
              </n-button>
            </div>
          </div>
        </div>

        <!-- 图片文件预览 -->
        <div v-else-if="previewData?.preview_type === 'image'" class="preview-image">
          <div class="image-header">
            <div class="image-title">
              <n-icon size="20" color="#722ed1">
                <Icon icon="mdi:image" />
              </n-icon>
              <span class="title-text">图片文件</span>
            </div>
            <div class="image-meta">
              <n-tag type="success" size="small">已下载</n-tag>
            </div>
          </div>

          <div class="image-content">
            <n-alert type="success" title="图片文件已下载">
              <template #icon>
                <n-icon>
                  <Icon icon="mdi:check-circle" />
                </n-icon>
              </template>
              <div class="image-info">
                <p><strong>本地路径：</strong></p>
                <n-text code copyable>{{ previewData.content }}</n-text>
                <p class="mt-2"><strong>文件大小：</strong> {{ formatFileSize(previewData.file_size || 0) }}</p>
              </div>
            </n-alert>

            <div class="image-actions">
              <n-button type="primary" @click="openFileLocation(previewData.content)">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:folder-open" />
                  </n-icon>
                </template>
                打开文件位置
              </n-button>
            </div>
          </div>
        </div>

        <!-- 其他文件类型 -->
        <div v-else class="preview-other">
          <div class="other-header">
            <div class="other-title">
              <n-icon size="20" color="#8c8c8c">
                <Icon icon="mdi:file" />
              </n-icon>
              <span class="title-text">文件预览</span>
            </div>
          </div>

          <div class="other-content">
            <n-alert type="warning" title="暂不支持预览此文件类型">
              <template #icon>
                <n-icon>
                  <Icon icon="mdi:information" />
                </n-icon>
              </template>
              <div class="other-info">
                <p>该文件类型暂不支持在线预览，您可以：</p>
                <ul>
                  <li>下载文件到本地查看</li>
                  <li>使用相应的专业软件打开</li>
                  <li>查看文件的基本信息</li>
                </ul>
              </div>
            </n-alert>
          </div>
        </div>
      </n-spin>
    </div>

    <!-- 视频预览模态框 -->
    <n-modal
      v-model:show="showVideoPlayer"
      preset="card"
      title="视频预览"
      style="width: 90vw; max-width: 1200px;"
      :mask-closable="false"
      :closable="true"
      @close="closeVideoPlayer"
    >
      <template #header>
        <div class="video-modal-header">
          <div class="video-title">
            <n-icon size="20" color="#52c41a">
              <Icon icon="mdi:play-circle" />
            </n-icon>
            <span>视频预览</span>
          </div>
          <div class="video-info">
            <n-text depth="3" style="font-size: 12px;">
              {{ fileName }}
            </n-text>
          </div>
        </div>
      </template>

      <div class="video-modal-content">
        <div class="video-container">
          <video
            ref="videoPlayer"
            :src="previewData?.content"
            controls
            preload="metadata"
            class="video-element"
            @loadstart="onVideoLoadStart"
            @loadedmetadata="onVideoLoadedMetadata"
            @error="onVideoError"
            @canplay="onVideoCanPlay"
            @pause="onVideoPause"
            @play="onVideoPlay"
          >
            您的浏览器不支持视频播放。
          </video>

          <!-- 加载状态 -->
          <div v-if="videoLoading" class="video-loading">
            <n-spin size="large">
              <template #description>
                <span style="color: white;">正在加载视频...</span>
              </template>
            </n-spin>
          </div>

          <!-- 错误状态 -->
          <div v-if="videoError" class="video-error">
            <n-result status="error" title="视频加载失败" :description="videoErrorMessage">
              <template #icon>
                <n-icon size="64" color="#ff6b6b">
                  <Icon icon="mdi:video-off" />
                </n-icon>
              </template>
              <template #footer>
                <n-space>
                  <n-button type="primary" @click="retryVideoLoad">
                    <template #icon>
                      <n-icon>
                        <Icon icon="mdi:refresh" />
                      </n-icon>
                    </template>
                    重试加载
                  </n-button>
                  <n-button @click="closeVideoPlayer">关闭</n-button>
                </n-space>
              </template>
            </n-result>
          </div>
        </div>

        <!-- 视频信息和操作 -->
        <div class="video-actions">
          <div class="video-url-info">
            <n-text depth="3" style="font-size: 12px;">
              视频链接：{{ previewData?.decoded_content || previewData?.content }}
            </n-text>
          </div>
          <div class="video-controls">
            <n-space>
              <n-button size="small" @click="copyToClipboard(previewData?.content)">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:content-copy" />
                  </n-icon>
                </template>
                复制链接
              </n-button>
              <n-button size="small" @click="openUrl(previewData?.content)">
                <template #icon>
                  <n-icon>
                    <Icon icon="mdi:open-in-new" />
                  </n-icon>
                </template>
                外部播放
              </n-button>
            </n-space>
          </div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import {
  NIcon,
  NSpin,
  NResult,
  NInput,
  NButton,
  NTag,
  NDescriptions,
  NDescriptionsItem,
  NText,
  NAlert,
  NModal,
  NSpace,
  useMessage
} from 'naive-ui';
import { Icon } from '@iconify/vue';
import { getFilePreview } from '@/service/api/strm';

// Props
interface Props {
  taskId: number;
  filePath: string;
}

const props = defineProps<Props>();

// 响应式数据
const loading = ref(false);
const previewData = ref<any>(null);
const showVideoPlayer = ref(false);
const videoLoading = ref(false);
const videoError = ref(false);
const videoErrorMessage = ref('');
const videoPlayer = ref<HTMLVideoElement>();
const message = useMessage();

// 计算属性
const fileName = computed(() => {
  return props.filePath.split('/').pop() || props.filePath;
});

const fileExtension = computed(() => {
  const name = fileName.value;
  const lastDot = name.lastIndexOf('.');
  return lastDot > 0 ? name.substring(lastDot) : '';
});

// 方法
const fetchPreview = async () => {
  loading.value = true;
  try {
    const { data } = await getFilePreview(props.taskId, props.filePath);
    previewData.value = data;
  } catch (error: any) {
    console.error('获取文件预览失败:', error);
    message.error(`获取文件预览失败: ${error.message || '未知错误'}`);
    previewData.value = {
      preview_type: 'error',
      error: error.message || '获取预览失败'
    };
  } finally {
    loading.value = false;
  }
};



const testVideoLink = async (url: string) => {
  try {
    message.info('正在测试链接可访问性...');

    // 使用HEAD请求测试链接
    const response = await fetch(url, {
      method: 'HEAD',
      mode: 'no-cors' // 避免CORS问题
    });

    message.success('链接测试成功，可以访问');
  } catch (error) {
    console.error('链接测试失败:', error);
    message.warning('链接测试失败，可能存在网络问题或链接无效');
  }
};

const toggleVideoPreview = () => {
  if (!showVideoPlayer.value) {
    // 打开视频预览模态框
    showVideoPlayer.value = true;
    // 重置视频状态
    videoError.value = false;
    videoErrorMessage.value = '';
    videoLoading.value = true;
  }
};

const closeVideoPlayer = () => {
  // 关闭视频播放器时暂停视频
  if (videoPlayer.value) {
    videoPlayer.value.pause();
  }
  showVideoPlayer.value = false;
  videoLoading.value = false;
  videoError.value = false;
  videoErrorMessage.value = '';
};

const onVideoLoadStart = () => {
  videoLoading.value = true;
  videoError.value = false;
  videoErrorMessage.value = '';
};

const onVideoLoadedMetadata = () => {
  videoLoading.value = false;
  console.log('视频元数据加载完成');
};

const onVideoError = (event: Event) => {
  videoLoading.value = false;
  videoError.value = true;

  const video = event.target as HTMLVideoElement;
  const error = video.error;

  let errorMessage = '视频加载失败';
  if (error) {
    switch (error.code) {
      case MediaError.MEDIA_ERR_ABORTED:
        errorMessage = '视频加载被中止';
        break;
      case MediaError.MEDIA_ERR_NETWORK:
        errorMessage = '网络错误，无法加载视频';
        break;
      case MediaError.MEDIA_ERR_DECODE:
        errorMessage = '视频解码错误，格式可能不支持';
        break;
      case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
        errorMessage = '视频格式不支持或链接无效';
        break;
      default:
        errorMessage = '未知错误';
    }
  }

  videoErrorMessage.value = errorMessage;
  console.error('视频加载错误:', errorMessage, error);
};

const onVideoCanPlay = () => {
  videoLoading.value = false;
  console.log('视频可以开始播放');
};

const retryVideoLoad = () => {
  if (videoPlayer.value) {
    videoError.value = false;
    videoErrorMessage.value = '';
    videoLoading.value = true;
    videoPlayer.value.load(); // 重新加载视频
  }
};

const onVideoPlay = () => {
  console.log('视频开始播放');
};

const onVideoPause = () => {
  console.log('视频暂停');
};

const openUrl = (url: string) => {
  try {
    window.open(url, '_blank');
  } catch (error) {
    console.error('打开链接失败:', error);
    message.error('打开链接失败');
  }
};

const getTextFileIcon = () => {
  const ext = fileExtension.value.toLowerCase();
  switch (ext) {
    case '.nfo':
      return 'mdi:information-outline';
    case '.xml':
      return 'mdi:code-tags';
    case '.json':
      return 'mdi:code-json';
    case '.srt':
    case '.ass':
    case '.vtt':
      return 'mdi:subtitles-outline';
    default:
      return 'mdi:file-document-outline';
  }
};

const getTextFileTitle = () => {
  const ext = fileExtension.value.toLowerCase();
  switch (ext) {
    case '.nfo':
      return 'NFO信息文件';
    case '.xml':
      return 'XML配置文件';
    case '.json':
      return 'JSON数据文件';
    case '.srt':
      return 'SRT字幕文件';
    case '.ass':
      return 'ASS字幕文件';
    case '.vtt':
      return 'VTT字幕文件';
    case '.txt':
      return '文本文件';
    default:
      return '文本文件';
  }
};

const getFileExtension = () => {
  return fileExtension.value.replace('.', '') || 'TXT';
};

const downloadTextFile = () => {
  if (!previewData.value?.content) {
    message.error('没有可下载的内容');
    return;
  }

  try {
    const blob = new Blob([previewData.value.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName.value;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success('文件下载成功');
  } catch (error) {
    console.error('下载失败:', error);
    message.error('文件下载失败');
  }
};

const openFileLocation = (filePath: string) => {
  // 这里可以实现打开文件位置的逻辑
  // 由于浏览器安全限制，通常需要后端支持
  message.info('请手动打开文件位置：' + filePath);
};



const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  } catch (error) {
    console.error('复制失败:', error);
    message.error('复制失败');
  }
};

// 生命周期
onMounted(() => {
  fetchPreview();
});
</script>

<style scoped>
.file-preview {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.preview-content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.preview-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

/* STRM文件预览样式 */
.preview-strm {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.strm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f6ffed 0%, #f0f9ff 100%);
  border-radius: 8px;
  border: 1px solid #b7eb8f;
}

.strm-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color-1);
}

.strm-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strm-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.video-link-section {
  background: var(--card-color);
  border-radius: 8px;
  padding: 20px;
  border: 1px solid var(--border-color);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-weight: 600;
  color: var(--text-color-1);
  font-size: 16px;
}

.link-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.link-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color-2);
  margin-bottom: 8px;
}

.link-display {
  width: 100%;
}

.link-input {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
}

.decoded-link {
  background-color: #f6ffed;
  border-color: #b7eb8f;
}

.link-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 12px;
}

/* 视频模态框样式 */
.video-modal-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.video-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.video-info {
  font-size: 12px;
  color: var(--text-color-3);
}

.video-modal-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.video-container {
  position: relative;
  background: #000;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
  min-height: 400px;
}

.video-element {
  width: 100%;
  height: auto;
  max-height: 70vh;
  min-height: 400px;
  display: block;
  object-fit: contain;
}

.video-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.8);
  z-index: 10;
}

.video-error {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.9);
  z-index: 10;
}

.video-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--card-color);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.video-url-info {
  word-break: break-all;
  max-height: 60px;
  overflow-y: auto;
}

.video-controls {
  display: flex;
  justify-content: flex-end;
}

.video-preview-hint {
  background: #f0f9ff;
  border-radius: 8px;
  padding: 16px;
}

.hint-content p {
  margin: 4px 0;
  color: var(--text-color-2);
}

/* 文本文件预览样式 */
.preview-text {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.text-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f0f9ff 0%, #f6ffed 100%);
  border-radius: 8px;
  border: 1px solid #91caff;
}

.text-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.text-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.content-length {
  font-size: 12px;
  color: var(--text-color-3);
}

.text-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.text-viewer {
  background: var(--card-color);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid var(--border-color);
}

.content-textarea {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.text-actions {
  display: flex;
  gap: 12px;
}

/* 图片文件预览样式 */
.preview-image {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.image-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #f9f0ff 0%, #f6ffed 100%);
  border-radius: 8px;
  border: 1px solid #d3adf7;
}

.image-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.image-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.image-info {
  margin-top: 8px;
}

.image-info p {
  margin: 8px 0;
}

.image-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

/* 其他文件类型样式 */
.preview-other {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.other-header {
  padding: 16px 20px;
  background: var(--card-color);
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

.other-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.other-content {
  background: var(--card-color);
  border-radius: 8px;
  padding: 20px;
  border: 1px solid var(--border-color);
}

.other-info ul {
  margin: 12px 0;
  padding-left: 20px;
}

.other-info li {
  margin: 4px 0;
  color: var(--text-color-2);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .preview-content {
    padding: 16px;
  }

  .strm-header,
  .text-header,
  .image-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .link-actions,
  .text-actions,
  .image-actions {
    flex-direction: column;
  }

  .link-actions .n-button,
  .text-actions .n-button,
  .image-actions .n-button {
    width: 100%;
  }

  /* 移动端视频模态框 */
  .video-element {
    max-height: 50vh;
    min-height: 250px;
  }

  .video-container {
    min-height: 250px;
  }

  .video-actions {
    padding: 12px;
  }

  .video-controls {
    justify-content: center;
  }

  .video-modal-content {
    gap: 12px;
  }
}
</style>
