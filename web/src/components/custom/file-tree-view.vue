<template>
  <div class="file-tree-view">
    <div v-if="isLoading" class="loading-state">
      <n-spin size="medium" />
      <p class="mt-2">加载目录结构中...</p>
    </div>
    <div v-else-if="treeData.length === 0" class="empty-state">
      <n-empty description="暂无目录数据" />
      <p class="mt-2 text-secondary-text">选定的目录为空或未找到符合条件的文件</p>
    </div>
    <n-tree v-else block-line remote :data="treeData" :default-expanded-keys="defaultExpandedKeys"
      :expanded-keys="expandedKeys" :pattern="searchPattern" :selectable="false" :checkable="false"
      :expand-on-click="true" :on-load="handleLoad" @update:expanded-keys="handleExpandedKeys" />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, type PropType, watch } from 'vue';
import { NEmpty, NSpin, NTree, type TreeOption, useMessage } from 'naive-ui';
import { getDirectoryContent, searchFiles } from '@/service/api/strm';

const message = useMessage();

const props = defineProps({
  recordId: {
    type: [String, Number],
    required: true
  },
  fileTypeFilter: {
    type: String,
    default: 'all'
  },
  searchValue: {
    type: String,
    default: ''
  },
  rootDirectories: {
    type: Array as PropType<string[]>,
    default: () => []
  },
  rootFiles: {
    type: Array as PropType<StrmAPI.ParsedFile[]>,
    default: () => []
  }
});

// 提供方法给父组件调用
const exposes = {
  performSearch
};
defineExpose(exposes);

// 搜索模式字符串
const searchPattern = computed(() => props.searchValue);

// 节点加载状态
const loadingKeys = ref<Set<string>>(new Set());
// 组件加载状态
const isLoading = ref(false);

// 默认展开的节点和当前展开的节点
const defaultExpandedKeys = ref<string[]>([]);
const expandedKeys = ref<string[]>([]);

// 树形数据
const treeData = ref<TreeOption[]>([]);

// 节点键值到路径的映射
const keyToPathMap = ref<Map<string, string>>(new Map());

// 查找树中的节点
const findTreeNode = (nodes: TreeOption[], key: string): TreeOption | null => {
  for (const node of nodes) {
    if (node.key === key) return node;
    if (node.children && node.children.length > 0) {
      const found = findTreeNode(node.children, key);
      if (found) return found;
    }
  }
  return null;
};

// 初始化树结构
const initTreeData = () => {
  // 创建根目录节点
  const rootNodes: TreeOption[] = [];

  // 添加根目录
  props.rootDirectories.forEach(dir => {
    const key = `dir:${dir}`;
    keyToPathMap.value.set(key, `/${dir}`);

    // 目录节点 - 使用children: true表示需要懒加载
    rootNodes.push({
      key,
      label: dir,
      prefix: () => h('span', { class: 'mr-1' }, '📁'),
      isLeaf: false,
      children: []  // 使用空数组，NTree组件会在展开时自动调用懒加载
    });
  });

  // 添加根目录中的文件
  props.rootFiles.forEach(file => {
    if (props.fileTypeFilter !== 'all' && file.file_type !== props.fileTypeFilter) {
      return;
    }

    // 文件节点 - isLeaf为true表示不可展开
    rootNodes.push({
      key: `file:${file.file_name}`,
      label: file.file_name,
      isLeaf: true,
      prefix: () => h('span', { class: 'mr-1' }, getFileEmoji(file.file_type || 'other', file.extension || '')),
      suffix: () => h('span', { class: 'ml-2 text-xs text-secondary-text' }, `(${file.extension || ''})`)
    });
  });

  treeData.value = rootNodes;

  // 默认不展开根节点，等待用户点击
  defaultExpandedKeys.value = [];
  expandedKeys.value = [];
};

// 异步加载子节点
const handleLoad = async (node: TreeOption) => {
  // 检查是否已经在加载
  if (loadingKeys.value.has(node.key as string)) {
    return;
  }

  // 标记为正在加载
  loadingKeys.value.add(node.key as string);

  try {
    // 获取该节点对应的路径
    const path = keyToPathMap.value.get(node.key as string);
    if (!path) {
      throw new Error(`未找到节点 ${node.key} 对应的路径`);
    }

    // 加载该目录下的内容
    const { data } = await getDirectoryContent(props.recordId, {
      directoryPath: path,
      fileType: props.fileTypeFilter
    });

    // 处理获取到的子目录和文件
    const children: TreeOption[] = [];

    if (data && data.items) {
      // 处理返回的items数组
      data.items.forEach(item => {
        // 检查是否为文件，判断文件的方法：
        // 1. 如果item.is_directory明确为true，则为目录
        // 2. 如果item.is_directory未定义，则检查文件名是否有扩展名
        const fileName = item.file_name;
        const isFile = !item.is_directory || hasFileExtension(fileName);

        if (!isFile) {
          // 如果是目录，提取目录名（从路径中）
          const dirPath = `${path}/${fileName}`;
          const dirKey = `dir:${dirPath}`;
          keyToPathMap.value.set(dirKey, dirPath);

          children.push({
            key: dirKey,
            label: fileName,
            prefix: () => h('span', { class: 'mr-1' }, '📁'),
            isLeaf: false,
            children: [] // 空数组，会在展开时调用懒加载函数
          });
        } else {
          // 如果是文件，直接添加
          children.push({
            key: `file:${path}/${fileName}`,
            label: fileName,
            isLeaf: true,
            prefix: () => h('span', { class: 'mr-1' }, getFileEmoji(item.file_type || 'other', item.extension || getFileExtension(fileName))),
            suffix: () => h('span', { class: 'ml-2 text-xs text-secondary-text' }, `(${item.extension || getFileExtension(fileName) || ''})`)
          });
        }
      });
    }

    // 更新节点的子节点
    if (node.children) {
      node.children = children;
    } else {
      node.children = children;
    }
  } catch (error: any) {
    console.error('加载目录内容失败', error);
    message.error(`加载目录内容失败: ${error.message || '未知错误'}`);
  } finally {
    // 移除加载状态
    loadingKeys.value.delete(node.key as string);
  }
};

// 检查文件名是否有扩展名
function hasFileExtension(fileName: string): boolean {
  // 移除可能的尾部斜杠
  const cleanName = fileName.endsWith('/') ? fileName.slice(0, -1) : fileName;

  // 检查是否有扩展名
  const parts = cleanName.split('.');
  return parts.length > 1 && parts[parts.length - 1].length > 0;
}

// 从文件名获取扩展名
function getFileExtension(fileName: string): string {
  // 移除可能的尾部斜杠
  const cleanName = fileName.endsWith('/') ? fileName.slice(0, -1) : fileName;

  const parts = cleanName.split('.');
  if (parts.length > 1) {
    return parts[parts.length - 1].toLowerCase();
  }
  return '';
}

// 更新展开的节点
const handleExpandedKeys = (keys: string[]) => {
  // 查找新增的键，这些是刚被展开的节点
  const newExpandedKeys = keys.filter(key => !expandedKeys.value.includes(key));
  if (newExpandedKeys.length > 0) {
    // 手动加载新展开节点的内容
    newExpandedKeys.forEach(key => {
      if (key.startsWith('dir:')) {
        const path = keyToPathMap.value.get(key);
        if (path) {
          const node = findTreeNode(treeData.value, key);
          if (node) {
            // 手动触发加载
            handleLoad(node);
          }
        }
      }
    });
  }

  expandedKeys.value = keys;
};

// 获取文件图标emoji
function getFileEmoji(fileType: string, extension?: string): string {
  // 基本文件类型图标
  const typeIconMap: Record<string, string> = {
    'video': '🎬',
    'audio': '🎵',
    'image': '🖼️',
    'subtitle': '📃',
    'metadata': '📋',
    'other': '📄'
  };

  // 特定扩展名的图标映射
  const extensionIconMap: Record<string, string> = {
    // 视频文件
    'mp4': '🎬',
    'mkv': '🎥',
    'avi': '🎬',
    'mov': '🎬',
    'wmv': '🎬',
    // 音频文件
    'mp3': '🎵',
    'flac': '🎼',
    'wav': '🎵',
    'aac': '🎵',
    'ogg': '🎵',
    // 图片文件
    'jpg': '🖼️',
    'jpeg': '🖼️',
    'png': '🖼️',
    'gif': '🎞️',
    'webp': '🖼️',
    'bmp': '🖼️',
    // 字幕文件
    'srt': '💬',
    'ass': '💬',
    'vtt': '💬',
    'sub': '💬',
    'idx': '💬',
    // 元数据文件
    'nfo': '📋',
    'txt': '📝',
    'xml': '🗂️',
    'json': '📊',
    // 归档文件
    'zip': '🗜️',
    'rar': '🗜️',
    '7z': '🗜️',
    'tar': '🗜️',
    'gz': '🗜️',
    // 其他文件
    'pdf': '📕',
    'doc': '📘',
    'docx': '📘',
    'xls': '📊',
    'xlsx': '📊'
  };

  // 先检查是否有特定扩展名的图标
  if (extension && extensionIconMap[extension.toLowerCase()]) {
    return extensionIconMap[extension.toLowerCase()];
  }

  // 没有特定扩展名图标则使用文件类型图标
  return typeIconMap[fileType] || '📄';
}

// 初始化
onMounted(() => {
  // 显示加载状态
  isLoading.value = true;

  // 延迟一下来确保UI能够显示加载状态
  setTimeout(() => {
    initTreeData();
    isLoading.value = false;

    // 为所有初始根节点创建路径映射，确保它们可以被正确加载
    treeData.value.forEach(node => {
      if (!node.isLeaf && node.key) {
        const key = node.key.toString();
        if (key.startsWith('dir:') && !keyToPathMap.value.has(key)) {
          const dirName = key.replace('dir:', '');
          keyToPathMap.value.set(key, `/${dirName}`);
        }
      }
    });
  }, 100);
});

// 添加对根目录和根文件的监听，确保它们变化时更新树形视图
watch([() => props.rootDirectories, () => props.rootFiles], ([newDirs, newFiles]) => {
  // 只有当数据实际发生变化时才重新初始化
  if (newDirs.length > 0 || newFiles.length > 0) {
    // 显示加载状态
    isLoading.value = true;

    // 短暂延迟以显示加载状态
    setTimeout(() => {
      initTreeData();
      isLoading.value = false;
    }, 100);
  }
}, { deep: true });

// 当文件类型过滤器变化时，重新初始化树结构
watch(() => props.fileTypeFilter, () => {
  initTreeData();
});

// 从搜索结果构建树形结构
const buildTreeFromSearchResults = (matches: StrmAPI.ParsedFile[]): TreeOption[] => {
  // 创建目录结构映射
  const dirMap = new Map<string, TreeOption>();
  const rootNodes: TreeOption[] = [];

  // 处理每个匹配的文件
  matches.forEach(file => {
    // 获取文件所在目录
    const dirPath = file.directory || '/';
    // 获取文件名
    const fileName = file.file_name;

    // 分解目录路径成各级目录
    const pathParts = dirPath.split('/').filter(Boolean);

    // 确保根目录存在
    if (!dirMap.has('/')) {
      const rootNode: TreeOption = {
        key: 'dir:/',
        label: '/',
        prefix: () => h('span', { class: 'mr-1' }, '📁'),
        children: [],
        isLeaf: false
      };
      dirMap.set('/', rootNode);
      rootNodes.push(rootNode);
    }

    // 创建目录结构
    let currentPath = '';
    let parentNode = dirMap.get('/');

    for (const part of pathParts) {
      currentPath = currentPath + '/' + part;

      if (!dirMap.has(currentPath)) {
        const newNode: TreeOption = {
          key: `dir:${currentPath}`,
          label: part,
          prefix: () => h('span', { class: 'mr-1' }, '📁'),
          children: [],
          isLeaf: false
        };
        dirMap.set(currentPath, newNode);

        if (parentNode && parentNode.children) {
          parentNode.children.push(newNode);
        }
      }

      parentNode = dirMap.get(currentPath);
    }

    // 添加文件节点到其所在目录
    if (parentNode && parentNode.children) {
      parentNode.children.push({
        key: `file:${dirPath}/${fileName}`,
        label: fileName,
        isLeaf: true,
        prefix: () => h('span', { class: 'mr-1' }, getFileEmoji(file.file_type || 'other', file.extension || '')),
        suffix: () => h('span', { class: 'ml-2 text-xs text-secondary-text' }, `(${file.extension || ''})`)
      });
    }
  });

  return rootNodes;
};

// 获取树中所有节点的键
const getAllKeys = (nodes: TreeOption[]): string[] => {
  let keys: string[] = [];

  nodes.forEach(node => {
    if (!node.isLeaf) {
      keys.push(node.key as string);
      if (node.children && node.children.length > 0) {
        keys = keys.concat(getAllKeys(node.children));
      }
    }
  });

  return keys;
};

/**
 * 服务端搜索功能
 * 手动调用此方法进行搜索，不再自动监听searchValue变化
 */
async function performSearch(searchValue: string) {
  if (!searchValue || searchValue.trim().length < 2) {
    // 如果搜索值为空或太短，重置为初始树结构
    initTreeData();
    expandedKeys.value = [];
    return;
  }

  const trimmedSearchValue = searchValue.trim();
  message.info(`正在搜索: "${trimmedSearchValue}"...`);
  isLoading.value = true;

  try {
    // 调用后端搜索API
    const { data } = await searchFiles(props.recordId, trimmedSearchValue, {
      fileType: props.fileTypeFilter,
      ignoreCase: true // 忽略大小写
    });

    if (data && data.matches && data.matches.length > 0) {
      // 重置树结构为搜索结果
      treeData.value = buildTreeFromSearchResults(data.matches);
      // 默认展开所有节点以显示搜索结果
      const allKeys = getAllKeys(treeData.value);
      expandedKeys.value = allKeys;
      defaultExpandedKeys.value = allKeys;

      message.success(`找到 ${data.total_matches} 个匹配项`);
    } else {
      message.info('未找到匹配项');
      // 清空树并显示无结果提示
      treeData.value = [];
    }
  } catch (error: any) {
    message.error(`搜索失败: ${error.message || '未知错误'}`);
  } finally {
    isLoading.value = false;
  }
}

// 移除对searchValue的自动监听，只保留对fileTypeFilter的监听
watch(() => props.fileTypeFilter, () => {
  initTreeData();
});
</script>

<style scoped>
.file-tree-view {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.loading-state,
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

.loading-state p,
.empty-state p {
  margin-top: 0.5rem;
  color: var(--n-text-color-disabled);
  font-size: 0.875rem;
}
</style>
