import { request } from '../request';

/**
 * Task type enum
 * - 'strm': STRM file generation task
 * - 'resource_download': Resource download task
 */
export type TaskType = 'strm' | 'resource_download';

// Extend the global StrmAPI namespace for type safety
declare global {
  namespace StrmAPI {
    interface ParsedFile {
      file_name: string;
      path: string;
      is_directory?: boolean;
      file_type?: string;
      mime_type?: string;
      extension?: string;
      directory?: string;
    }
  }
}

/**
 * 上传115目录树文件
 *
 * @param file 要上传的文件
 */
export function uploadDirectoryTree(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  return request<StrmAPI.UploadResult>({
    url: '/strm/upload',
    method: 'post',
    data: formData
  });
}

/**
 * 通过URL上传115目录树文件
 *
 * @param url 文件的URL地址
 * @param onProgress 下载进度回调函数 (percent: number) => void
 * @param timeoutMs 超时时间（毫秒），默认为60秒
 */
export function uploadDirectoryTreeFromUrl(url: string, onProgress?: (percent: number) => void, timeoutMs: number = 60000) {
  return request<StrmAPI.UploadResult>({
    url: '/strm/upload-url',
    method: 'post',
    data: { url },
    // 为URL上传设置更长的超时时间，因为需要从远程服务器下载文件
    timeout: timeoutMs,
    onDownloadProgress: event => {
      if (onProgress && event.total) {
        // 只有当total存在（服务器返回Content-Length）时才能计算精确进度
        const percent = Math.round((event.loaded * 100) / event.total);
        onProgress(percent);
      } else if (onProgress && event.loaded > 0) {
        // 当无法获取total时，提供不精确的进度指示（基于已下载的字节数）
        // 这种情况下最多只显示到95%，最后5%在上传成功后设置
        const estimatedPercent = Math.min(95, Math.round(event.loaded / 10240)); // 假设平均文件大小为1MB
        onProgress(estimatedPercent);
      }
    }
  });
}

/**
 * 解析已上传的115目录树文件
 *
 * @param data 包含记录ID的对象
 */
export function parseDirectoryTree(data: { record_id: string | number; file_path?: string }) {
  return request<StrmAPI.ParseResult>({
    url: '/strm/parse',
    method: 'post',
    data
  });
}

/**
 * 获取媒体服务器列表
 * @param serverType 可选的服务器类型过滤
 */
export function getMediaServers(serverType?: string) {
  return request({
    url: '/strm/servers',
    method: 'get',
    params: serverType ? { server_type: serverType } : {}
  });
}

/**
 * 创建STRM生成任务
 * @param data 任务数据
 */
export function createStrmTask(data: Record<string, any>) {
  return request({
    url: '/strm/generate',
    method: 'post',
    data: {
      ...data,
      task_type: 'strm' // 默认为STRM生成任务
    }
  });
}

/**
 * 生成STRM文件
 * @param data 生成所需的数据，包含threads(下载线程数)参数
 */
export function generateStrm(data: Record<string, any>) {
  // 使用更短的超时，因为这个请求应该很快返回，若长时间无响应则可能是服务器问题
  const timeoutMs = 10000; // 10秒超时

  return request({
    url: '/strm/generate',
    method: 'post',
    data,
    timeout: timeoutMs
  });
}

/**
 * 获取任务列表
 * @param params 查询参数
 */
export function getTaskList(params?: Record<string, any>) {
  return request<StrmAPI.StrmTaskResponse>({
    url: '/strm/tasks',
    method: 'get',
    params
  });
}

/**
 * 获取任务状态
 * @param taskId 任务ID
 */
export function getTaskStatus(taskId: number) {
  return request<StrmAPI.StrmTaskDetail>({
    url: `/strm/task/${taskId}`,
    method: 'get'
  });
}

/**
 * 获取任务文件列表
 * @param taskId 任务ID
 * @param page 页码
 * @param pageSize 每页数量
 * @param filters 过滤条件
 */
export function getTaskFiles(
  taskId: number,
  page: number = 1,
  pageSize: number = 10,
  filters?: {
    fileType?: string;
    search?: string;
    status?: string;
  }
) {
  const params: any = { page, page_size: pageSize };

  if (filters?.fileType) {
    params.file_type = filters.fileType;
  }
  if (filters?.search) {
    params.search = filters.search;
  }
  if (filters?.status) {
    params.status = filters.status;
  }

  return request<{
    files: any[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      pages: number;
    };
    stats: {
      total: number;
      success: number;
      failed: number;
      pending: number;
      processing: number;
    };
  }>({
    url: `/strm/task/${taskId}/files`,
    method: 'get',
    params
  });
}

/**
 * 获取任务目录内容（用于树形视图懒加载）
 * @param taskId 任务ID
 * @param options 可选参数对象 {directoryPath}
 * @returns 包含目录下文件和子目录的结果
 */
export function getTaskDirectoryContent(
  taskId: number,
  options: { directoryPath?: string } = {}
) {
  const { directoryPath = '/' } = options;

  return request<{
    directory_path: string;
    items: Array<{
      file_name: string;
      name?: string;
      is_directory: boolean;
      file_size?: number;
      size?: number;
      is_success?: boolean;
      file_type?: string;
    }>;
    stats: {
      file_count: number;
      directory_count: number;
    };
  }>({
    url: `/strm/task/${taskId}/directory`,
    method: 'get',
    params: { directory_path: directoryPath }
  });
}

/**
 * 取消任务
 * @param taskId 任务ID
 */
export function cancelTask(taskId: number) {
  return request({
    url: `/strm/task/${taskId}/cancel`,
    method: 'post'
  });
}

/**
 * 继续已取消的任务
 * @param taskId 任务ID
 */
export function continueTask(taskId: number) {
  return request({
    url: `/strm/task/${taskId}/continue`,
    method: 'post'
  });
}

/**
 * 删除任务
 * @param taskId 任务ID
 */
export function deleteTask(taskId: number) {
  return request({
    url: `/strm/task/${taskId}`,
    method: 'delete'
  });
}

/**
 * 获取文件上传历史
 * @param params 查询参数
 */
export function getUploadHistory(params?: Record<string, any>) {
  return request({
    url: '/strm/history',
    method: 'get',
    params
  });
}

/**
 * 获取文件解析结果，支持按文件类型过滤和分页
 *
 * @param recordId 记录ID
 * @param options 可选参数对象 {fileType, page, pageSize}
 * @returns 过滤和分页后的解析结果
 */
export function getParseResult(
  recordId: string | number,
  options: { fileType?: string; page?: number; pageSize?: number; allFiles?: boolean } = {}
) {
  const { fileType = 'all', page = 1, pageSize = 10, allFiles = false } = options;

  return request<StrmAPI.ParseResult>({
    url: `/strm/result/${recordId}`,
    method: 'get',
    params: { file_type: fileType, page, page_size: pageSize, all_files: allFiles }
  });
}

/**
 * 获取目录内容（采用懒加载方式）
 *
 * @param recordId 记录ID
 * @param options 可选参数对象 {directoryPath, fileType}
 * @returns 包含目录下文件和子目录的结果
 */
export function getDirectoryContent(
  recordId: string | number,
  options: { directoryPath?: string; fileType?: string } = {}
) {
  // 规范化路径，确保以斜杠开始和结束
  let normalizedPath = options.directoryPath || '/';

  // 检查这个路径是否是一个文件路径 (有文件扩展名)
  const hasFileExtension = (path: string) => {
    // 移除潜在的尾部斜杠
    const cleanPath = path.endsWith('/') ? path.slice(0, -1) : path;
    const fileName = cleanPath.split('/').pop() || '';
    const parts = fileName.split('.');
    return parts.length > 1 && parts[parts.length - 1].length > 0;
  };

  // 如果路径看起来是一个文件路径 (有扩展名)，尝试获取其所在目录
  if (hasFileExtension(normalizedPath)) {
    normalizedPath = normalizedPath.split('/').slice(0, -1).join('/') || '/';
  }

  // 确保路径以斜杠结束
  if (!normalizedPath.endsWith('/')) {
    normalizedPath += '/';
  }

  const { fileType = 'all' } = options;

  return request<{
    path: string;
    total: number;
    page: number;
    page_size: number;
    items: Array<{
      file_name: string;
      path: string;
      is_directory?: boolean;
      file_type?: string;
      mime_type?: string;
      extension?: string;
      directory?: string;
    }>;
    file_type: string;
    updated_by_version_check: boolean;
  }>({
    url: `/strm/directory/${recordId}`,
    method: 'get',
    params: { directory_path: normalizedPath, file_type: fileType }
  });
}

/**
 * 搜索文件
 *
 * @param recordId 记录ID
 * @param searchText 搜索文本
 * @param options 可选参数，包括文件类型过滤和是否忽略大小写
 * @returns 搜索结果
 */
export function searchFiles(
  recordId: string | number,
  searchText: string,
  options: { fileType?: string; ignoreCase?: boolean } = {}
) {
  const { fileType = 'all', ignoreCase = true } = options;

  return request<{
    search_text: string;
    ignore_case: boolean;
    file_type: string;
    total_matches: number;
    matches: StrmAPI.ParsedFile[];
  }>({
    url: `/strm/search/${recordId}`,
    method: 'get',
    params: { search_text: searchText, file_type: fileType, ignore_case: ignoreCase }
  });
}

/**
 * 获取STRM文件下载链接
 *
 * @param taskId 任务ID
 * @returns 完整的下载URL
 */
export function getStrmDownloadUrl(taskId: string | number): string {
  // 获取基础URL，确保与其他API请求一致
  const baseURL = import.meta.env.VITE_SERVICE_BASE_URL || '';
  return `${baseURL}/strm/download-strm/${taskId}`;
}

/**
 * 获取系统设置
 */
export function getSystemSettings() {
  return request({
    url: '/system-manage/settings',
    method: 'get'
  });
}

/**
 * 更新系统设置
 * @param data 设置数据
 */
export function updateSystemSettings(data: Record<string, any>) {
  return request({
    url: '/system-manage/settings',
    method: 'post',
    data
  });
}

/**
 * 删除上传记录
 * @param recordId 记录ID
 */
export function deleteUploadRecord(recordId: number) {
  return request({
    url: `/strm/history/${recordId}`,
    method: 'delete'
  });
}

/**
 * 获取文件下载URL
 *
 * @param recordId 记录ID
 * @returns 下载URL
 */
export function getDownloadUrl(recordId: number): string {
  // 获取基础URL，确保与其他API请求一致
  const baseURL = import.meta.env.VITE_SERVICE_BASE_URL || '';
  return `${baseURL}/strm/download/${recordId}`;
}

/**
 * 创建媒体服务器
 * @param data 服务器数据
 */
export function createMediaServer(data: Record<string, any>) {
  return request({
    url: '/strm/server',
    method: 'post',
    data
  });
}

/**
 * 更新媒体服务器
 * @param serverId 服务器ID
 * @param data 服务器数据
 */
export function updateMediaServer(serverId: number, data: Record<string, any>) {
  return request({
    url: `/strm/server/${serverId}`,
    method: 'put',
    data
  });
}

/**
 * 删除媒体服务器
 * @param serverId 服务器ID
 */
export function deleteMediaServer(serverId: number) {
  return request({
    url: `/strm/server/${serverId}`,
    method: 'delete'
  });
}

/**
 * 获取任务日志
 * @param taskId 任务ID
 * @param params 查询参数
 */
export function getTaskLogs(taskId: number, params?: {
  page?: number;
  page_size?: number;
  level?: string;
  search?: string;
  log_type?: string;
}) {
  return request({
    url: `/strm/task/${taskId}/logs`,
    method: 'get',
    params
  });
}

/**
 * 测试媒体服务器连接
 * @param serverId 服务器ID（可以为0，表示测试临时服务器）
 * @param tempServer 临时服务器对象（可选，当serverId为0时使用）
 */
export function testServerConnection(serverId: number, tempServer?: Record<string, any>) {
  // 如果是测试新服务器（未保存的服务器）
  if (serverId === 0 && tempServer) {
    // 使用新的API端点测试未保存的服务器
    return request({
      url: `/strm/server/test`,
      method: 'post',
      data: tempServer
    });
  }

  // 测试已有服务器
  return request({
    url: `/strm/server/${serverId}/test`,
    method: 'post'
  });
}

// createResourceDownloadTask API已删除，现在所有任务通过generateStrm创建

/**
 * 获取资源下载文件的进度
 * @param taskId 任务ID
 */
export function getDownloadProgress(taskId: number) {
  return request({
    url: `/strm/task/${taskId}/progress`,
    method: 'get'
  });
}

/**
 * 获取任务文件预览
 * @param taskId 任务ID
 * @param filePath 源文件路径（115网盘中的原始路径），用于查找对应的处理结果
 */
export function getFilePreview(taskId: number, filePath: string) {
  return request<{
    file_path: string;        // 源文件路径
    target_path?: string;     // 目标文件路径（实际预览的文件）
    file_type: string;        // 文件类型
    file_extension: string;   // 目标文件扩展名
    file_size?: number;       // 文件大小
    status: string;           // 处理状态
    preview_type: 'strm' | 'text' | 'image' | 'info' | 'error';
    content?: string;         // 文件内容（STRM文件的原始编码URL或文本文件内容）
    decoded_content?: string; // 解码后的URL（仅STRM文件）
    content_type?: string;    // 内容类型
    error?: string;           // 错误信息
  }>({
    url: `/strm/task/${taskId}/file/preview`,
    method: 'get',
    params: { file_path: filePath }
  });
}
