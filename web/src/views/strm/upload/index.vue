<template>
  <div>
    <n-card title="115 目录树文件上传" :bordered="false" class="h-full rounded-8px shadow-sm">
      <n-upload multiple directory-dnd :max="5" accept=".txt" :custom-request="customRequest"
        @before-upload="handleBeforeUpload">
        <n-upload-dragger>
          <div class="flex-col-center">
            <icon-mdi-upload class="text-68px text-primary" />
            <p class="mt-12px text-16px text-primary">点击或拖拽文件到这里上传</p>
            <p class="mt-8px text-12px text-secondary-text">
              请上传从115网盘导出的 .txt 格式的目录树文件。
            </p>
          </div>
        </n-upload-dragger>
      </n-upload>

      <!-- URL上传区域 -->
      <div class="mt-16px">
        <n-divider>或者通过URL上传</n-divider>
        <n-input-group>
          <n-input v-model:value="uploadUrl" placeholder="输入115目录树文件URL" :status="urlError ? 'error' : undefined"
            @input="checkUrl(uploadUrl)" @blur="checkUrl(uploadUrl)" />
          <n-button type="primary" :disabled="!uploadUrl.trim() || !!urlError || urlUploading" :loading="urlUploading"
            @click="handleUrlUpload">
            上传
          </n-button>
        </n-input-group>
        <p v-if="urlError" :class="[
          'mt-4px text-12px',
          isTxtFileUrl(uploadUrl) ? 'text-warning' : 'text-error'
        ]">
          {{ urlError }}
        </p>
        <p v-else class="mt-4px text-12px text-secondary-text">
          请输入指向115网盘导出的 .txt 格式目录树文件的URL地址。
        </p>

        <!-- URL上传进度条 -->
        <div v-if="urlUploading && uploadProgress > 0" class="mt-10px">
          <n-progress type="line" :percentage="uploadProgress" :height="12" :border-radius="4"
            :processing="uploadProgress < 100" :indicator-text-color="uploadProgress === 100 ? '#18a058' : undefined"
            :status="uploadProgress === 100 ? 'success' : 'default'">
            <template #default="slotProps">
              {{ uploadStatus }} {{ slotProps?.percentage || uploadProgress }}%
            </template>
          </n-progress>
        </div>
      </div>

      <!-- 解析结果展示 -->
      <div v-if="uploadedFiles.length > 0" class="mt-24px">
        <n-divider />
        <h3 class="mb-12px">已上传文件</h3>
        <n-space vertical>
          <n-card v-for="(file, index) in uploadedFiles" :key="file.path" size="small" class="mb-12px">
            <div class="flex items-center justify-between">
              <div>
                <div class="text-16px font-medium">{{ file.filename }}</div>
                <div class="text-12px text-secondary-text">{{ file.path }}</div>
              </div>
              <div>
                <n-button :loading="file.parsing" :disabled="file.parsed" type="primary"
                  @click="handleParseFile(file, index)">
                  {{ file.parsed ? '已解析' : '解析文件' }}
                </n-button>
              </div>
            </div>

            <!-- 解析结果 -->
            <div v-if="file.parseResult && currentFileIndex === index" class="mt-16px">
              <n-divider />
              <file-parse-result :record-id="file.recordId" :parse-result="file.parseResult" :loading="resultLoading"
                :show-info="false" @update:loading="resultLoading = $event"
                @file-page-change="handleFileParseResultPageChange" ref="fileParseResultRef" />

              <!-- 替换STRM生成组件为跳转按钮 -->
              <n-divider />
              <n-space justify="center">
                <n-button type="primary" :disabled="!file.parseResult?.stats?.video"
                  @click="goToStrmGenerate(file.recordId)">
                  <template #icon>
                    <icon-mdi-file-export />
                  </template>
                  生成STRM文件
                </n-button>
              </n-space>
            </div>
          </n-card>
        </n-space>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useMessage } from 'naive-ui';
import { useRouter } from 'vue-router';
import type {
  UploadCustomRequestOptions,
  UploadFileInfo
} from 'naive-ui';
import FileParseResult from '@/components/custom/file-parse-result.vue';
import {
  getParseResult,
  parseDirectoryTree,
  uploadDirectoryTree,
  uploadDirectoryTreeFromUrl
} from '@/service/api/strm';

defineOptions({
  name: 'StrmUpload'
});

const message = useMessage();
const router = useRouter();

// URL上传相关
const uploadUrl = ref('');
const urlUploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref('下载中');
const urlError = ref<string | null>(null);

// 检查URL是否有效 - 用于URL验证逻辑
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const isValidUrl = (url: string): boolean => {
  try {
    // 创建URL对象，如果格式无效会抛出错误
    const urlObj = new URL(url);

    // 检查协议是否是http或https
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      return false;
    }

    // 获取主机名
    const hostname = urlObj.hostname;

    // 检查主机名长度 - 通常主机名不会超过255个字符
    if (!hostname || hostname.length > 255) {
      return false;
    }

    // 检查主机名格式 - 使用正则表达式验证基本格式
    // 主机名应该是 example.com 或 sub.example.com 这样的格式
    // 允许字母、数字、点和连字符，并且需要至少有一个点分隔域名部分
    const hostnameRegex = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
    if (!hostnameRegex.test(hostname)) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
};

// 检查URL是否指向.txt文件
const isTxtFileUrl = (url: string): boolean => {
  // 检查URL是否以.txt结尾（不区分大小写）
  return url.toLowerCase().endsWith('.txt');
};

// 检查URL并设置错误信息
const checkUrl = (url: string): boolean => {
  if (!url || !url.trim()) {
    urlError.value = null; // 空输入不显示错误
    return false;
  }

  try {
    // 尝试创建URL对象进行初步检查
    const urlObj = new URL(url);

    // 检查协议
    if (!['http:', 'https:'].includes(urlObj.protocol)) {
      urlError.value = '请使用http或https协议的URL地址';
      return false;
    }

    // 获取主机名并检查
    const hostname = urlObj.hostname;

    // 检查主机名长度
    if (!hostname || hostname.length > 255) {
      urlError.value = '域名长度异常，请检查URL是否正确';
      return false;
    }

    // 检查主机名格式
    const hostnameRegex = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
    if (!hostnameRegex.test(hostname)) {
      urlError.value = '域名格式无效，请输入正确的网络地址';
      return false;
    }

    // 不强制要求以.txt结尾，但给出警告
    if (!isTxtFileUrl(url)) {
      urlError.value = '建议使用指向.txt格式文件的链接，其他格式可能无法正确解析';
      // 返回true但显示警告，让用户自行决定是否继续
      return true;
    }

    urlError.value = null;
    return true;
  } catch {
    urlError.value = '请输入有效的http或https URL地址';
    return false;
  }
};

// 上传文件列表
const uploadedFiles = ref<Array<{
  filename: string;
  path: string;
  recordId: string | number;
  parsing: boolean;
  parsed: boolean;
  parseResult?: StrmAPI.ParseResult;
}>>([]);

// 当前查看的文件索引
const currentFileIndex = ref(-1);

// 加载状态
const resultLoading = ref(false);

// 文件解析结果组件引用
const fileParseResultRef = ref<InstanceType<typeof FileParseResult> | null>(null);

const handleBeforeUpload = async (data: { file: UploadFileInfo; fileList: UploadFileInfo[] }): Promise<boolean> => {
  if (!data.file.file?.type.includes('text/plain')) {
    message.error('只能上传 .txt 格式的文件，请重新上传');
    return false;
  }
  if (data.file.file.size > 10 * 1024 * 1024) {
    message.error('文件大小不能超过 10MB，请重新上传');
    return false;
  }
  return true;
};

const customRequest = ({ file, onFinish, onError }: UploadCustomRequestOptions) => {
  uploadDirectoryTree(file.file as File)
    .then(response => {
      // 处理可能的类型问题，确保安全访问
      if (response?.data && typeof response.data === 'object') {
        const uploadResult = response.data as StrmAPI.UploadResult;
        message.success(`'${file.name}' 上传成功`);

        // 添加到已上传文件列表
        uploadedFiles.value.push({
          filename: uploadResult.filename,
          path: uploadResult.path,
          recordId: uploadResult.record_id,
          parsing: false,
          parsed: false
        });

        onFinish();
      } else {
        message.error(`'${file.name}' 上传失败: 服务器响应格式不正确`);
        onError();
      }
    })
    .catch(error => {
      message.error(`'${file.name}' 上传失败: ${error.message || '未知错误'}`);
      onError();
    });
};

// 跳转到STRM生成页面
const goToStrmGenerate = (recordId: string | number) => {
  // 将记录ID存储在会话存储中，以便目标页面可以获取
  sessionStorage.setItem('selected_record_id', String(recordId));
  // 跳转到STRM生成页面
  router.push('/strm/generate');
};

// 处理文件解析结果分页变化
const handleFileParseResultPageChange = async (params: { page: number; pageSize: number; fileType?: string }) => {
  if (currentFileIndex.value < 0 || !uploadedFiles.value[currentFileIndex.value]) return;

  const currentFile = uploadedFiles.value[currentFileIndex.value];
  resultLoading.value = true;

  try {
    // 构建参数
    const options = {
      fileType: params.fileType || 'all', // 使用传入的fileType或默认获取全部类型
      page: params.page,
      pageSize: params.pageSize
    };

    // 获取解析结果
    const result = await getParseResult(currentFile.recordId, options);
    if (result?.data) {
      currentFile.parseResult = result.data;
    }
  } catch (error: any) {
    message.error(`获取解析结果失败: ${error.message || '未知错误'}`);
  } finally {
    resultLoading.value = false;
  }
};

// 处理解析文件
const handleParseFile = async (file: any, index: number) => {
  if (file.parsed) {
    currentFileIndex.value = index;
    return;
  }

  file.parsing = true;
  resultLoading.value = true;

  try {
    // 1. 首先调用parseDirectoryTree解析文件
    const parseResult = await parseDirectoryTree({
      record_id: file.recordId
    });

    if (parseResult?.data) {
      // 2. 标记文件已解析
      file.parsed = true;
      currentFileIndex.value = index;

      // 3. 由于后端现在返回的是不包含文件列表的简化结果
      // 我们需要立即调用getParseResult获取第一页数据
      const defaultParams = {
        fileType: 'all',
        page: 1,
        pageSize: 10
      };

      const result = await getParseResult(file.recordId, defaultParams);
      if (result?.data) {
        // 4. 保存完整的解析结果（包含分页数据）
        file.parseResult = result.data;
      } else {
        // 5. 如果获取分页数据失败，至少保存基本的统计信息
        file.parseResult = parseResult.data;
      }
    }
  } catch (error: any) {
    message.error(error.message || '文件解析失败');
  } finally {
    file.parsing = false;
    resultLoading.value = false;
  }
};

// URL上传处理函数
const handleUrlUpload = async () => {
  const url = uploadUrl.value.trim();
  if (!url) {
    message.warning('请输入URL');
    return;
  }

  // 验证URL格式
  if (!checkUrl(url)) {
    message.error(urlError.value || '请输入有效的URL');
    return;
  }

  try {
    // 重置进度状态
    uploadProgress.value = 0;
    uploadStatus.value = '准备下载';
    urlUploading.value = true;

    // 创建进度回调函数
    const handleProgress = (percent: number) => {
      // 确保组件仍然挂载，并且上传状态仍然为true
      if (urlUploading.value) {
        // 确保percent是一个有效数字
        const validPercent = Number.isFinite(percent) ? percent : 0;
        uploadProgress.value = validPercent;

        // 根据进度更新状态文本
        if (validPercent < 50) {
          uploadStatus.value = '下载中';
        } else if (validPercent < 90) {
          uploadStatus.value = '处理中';
        } else if (validPercent < 100) {
          uploadStatus.value = '完成处理';
        } else {
          uploadStatus.value = '上传成功';
        }
      }
    };

    // 设置120秒超时时间（2分钟），足够处理大多数文件
    const { data } = await uploadDirectoryTreeFromUrl(url, handleProgress, 120000);

    // 无论服务器是否提供了进度，确保在成功时显示100%
    // 确保组件仍然挂载
    if (urlUploading.value) {
      uploadProgress.value = 100;
      uploadStatus.value = '上传成功';
    }

    if (data) {
      message.success(`URL文件上传成功, 已保存到: ${data.path}`);

      // 添加到已上传文件列表
      uploadedFiles.value.push({
        filename: data.filename,
        path: data.path,
        recordId: data.record_id,
        parsing: false,
        parsed: false
      });

      // 清空输入框
      uploadUrl.value = '';

      // 延迟1秒后重置进度显示（让用户有时间看到100%完成状态）
      setTimeout(() => {
        if (urlUploading.value) { // 确保组件状态仍然有效
          uploadProgress.value = 0;
        }
      }, 1000);
    }
  } catch (error: any) {
    uploadStatus.value = '上传失败';
    uploadProgress.value = 0; // 重置进度

    // 判断错误类型，提供更详细的错误信息
    if (error.message?.includes('timeout')) {
      // 提供超时错误的详细信息和建议
      message.error('URL上传超时，可能是文件太大或网络问题。建议：1.选择更小的文件；2.检查URL是否有效；3.确保文件所在服务器响应迅速。');
    } else if (error.response?.status === 404) {
      message.error('文件不存在或无法访问，请检查URL是否正确。');
    } else if (error.message?.includes('network')) {
      message.error('网络连接异常，请检查您的网络连接并重试。');
    } else {
      message.error(`URL上传失败: ${error.message || '未知错误'}`);
    }

    // 在控制台记录详细错误，便于调试
    console.error('URL上传错误详情:', error);
  } finally {
    // 保持进度条显示一会儿，然后再重置urlUploading
    setTimeout(() => {
      if (urlUploading.value) { // 添加额外检查，确保状态在更新前仍然有效
        urlUploading.value = false;
      }
    }, 1500);
  }
};
</script>

<style scoped>
.text-error {
  color: #d03050;
}

.text-warning {
  color: #f0a020;
}
</style>
