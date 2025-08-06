<template>
  <div class="file-tree-view">
    <div v-if="loading" class="loading-state">
      <n-spin size="medium" />
      <p class="mt-2">加载文件树中...</p>
    </div>
    <div v-else-if="treeData.length === 0" class="empty-state">
      <n-empty description="暂无文件数据" />
      <p class="mt-2 text-secondary-text">没有找到可显示的文件</p>
    </div>
    <div v-else class="tree-container">
      <!-- 搜索框 -->
      <div class="tree-search">
        <n-input
          v-model:value="searchPattern"
          placeholder="搜索文件..."
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <n-icon>
              <Icon icon="mdi:magnify" />
            </n-icon>
          </template>
        </n-input>
      </div>

      <!-- 树形结构 -->
      <n-tree
        block-line
        remote
        :data="treeData"
        :default-expanded-keys="defaultExpandedKeys"
        :expanded-keys="expandedKeys"
        :pattern="searchPattern"
        :selectable="false"
        :checkable="false"
        :expand-on-click="true"
        :on-load="handleLoad"
        @update:expanded-keys="handleExpandedKeys"
        @update:selected-keys="handleNodeClick"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref, watch, onMounted } from 'vue';
import type { TreeOption } from 'naive-ui';
import { NEmpty, NIcon, NInput, NSpin, NTree, NTag, useMessage } from 'naive-ui';
import { Icon } from '@iconify/vue';
import { getTaskDirectoryContent } from '@/service/api/strm';

// Props
interface Props {
  files: any[];
  loading?: boolean;
  taskId?: number;
  useLazyLoad?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  useLazyLoad: false
});

// Emits
const emit = defineEmits<{
  fileClick: [file: any];
}>();

// 响应式数据
const searchPattern = ref('');
const expandedKeys = ref<string[]>([]);
const defaultExpandedKeys = ref<string[]>([]);
const treeData = ref<TreeOption[]>([]);

// 懒加载相关
const message = useMessage();
const loadingKeys = ref<Set<string>>(new Set());
const keyToPathMap = ref<Map<string, string>>(new Map());

// 懒加载处理函数
const handleLoad = (node: TreeOption): Promise<void> => {
  console.log('handleLoad 被调用', {
    nodeKey: node.key,
    nodeLabel: node.label,
    useLazyLoad: props.useLazyLoad,
    taskId: props.taskId
  });

  return new Promise(async (resolve, reject) => {
    if (!props.useLazyLoad || !props.taskId) {
      console.warn('懒加载条件不满足', { useLazyLoad: props.useLazyLoad, taskId: props.taskId });
      resolve();
      return;
    }

    // 检查是否已经在加载
    if (loadingKeys.value.has(node.key as string)) {
      console.log('节点已在加载中，跳过', node.key);
      resolve();
      return;
    }

    // 检查节点是否已经有子节点（已加载过）
    if (node.children && Array.isArray(node.children) && node.children.length > 0) {
      console.log('节点已有子节点，跳过加载', node.key, node.children.length);
      resolve();
      return;
    }

    // 标记为正在加载
    loadingKeys.value.add(node.key as string);
    console.log('开始加载节点', node.key);

    try {
      // 获取该节点对应的路径
      const path = keyToPathMap.value.get(node.key as string);
      if (!path) {
        throw new Error(`未找到节点 ${node.key} 对应的路径`);
      }

      console.log('懒加载子目录:', { nodeKey: node.key, path });

      let children: TreeOption[] = [];

      try {
        // 尝试调用 API 加载该目录下的内容
        const { data } = await getTaskDirectoryContent(props.taskId, {
          directoryPath: path
        });

        console.log('API 返回子目录数据:', data);

        if (data && data.items) {
          // 处理返回的items数组
          data.items.forEach(item => {
            const fileName = item.file_name || item.name;
            const isFile = !item.is_directory;
            const childPath = `${path}/${fileName}`.replace(/\/+/g, '/');
            const key = `${isFile ? 'file' : 'dir'}-${childPath}`;

            // 记录路径映射
            if (!isFile) {
              keyToPathMap.value.set(key, childPath);
            }

            const childNodeConfig: TreeOption = {
              key,
              label: fileName,
              isLeaf: isFile,
              prefix: () => getNodeIconForItem(item, isFile),
              suffix: () => getNodeSuffixForItem(item, isFile)
            };

            // 对于目录，不设置 children 属性，让 Naive UI 自动处理懒加载
            if (isFile) {
              childNodeConfig.children = undefined;
            }

            children.push(childNodeConfig);
          });
        }
      } catch (apiError: any) {
        console.warn('API 调用失败，回退到本地数据:', apiError);

        // 回退到使用 props.files 数据
        children = loadChildrenFromFiles(path);
      }

      console.log('子目录加载完成，子节点数量:', children.length);
      console.log('返回的子节点:', children);

      // 直接设置节点的子节点
      node.children = children;

      // 移除加载状态
      loadingKeys.value.delete(node.key as string);

      console.log('Promise resolve，节点更新完成');
      resolve();
    } catch (error: any) {
      console.error('加载子目录失败:', error);
      message.error(`加载目录内容失败: ${error.message || '未知错误'}`);

      // 移除加载状态
      loadingKeys.value.delete(node.key as string);

      reject(error);
    }
  });
};

// 从本地文件数据加载子目录内容（回退方案）
const loadChildrenFromFiles = (targetPath: string): TreeOption[] => {
  const children: TreeOption[] = [];
  const directories = new Set<string>();
  const files: any[] = [];

  // 标准化目标路径
  const normalizedTargetPath = targetPath.replace(/^\/+/, '').replace(/\/+$/, '');
  const targetPrefix = normalizedTargetPath ? `${normalizedTargetPath}/` : '';

  console.log('从本地数据加载子目录:', { targetPath, normalizedTargetPath, targetPrefix });

  // 遍历所有文件，找到该目录下的直接子项
  props.files.forEach(file => {
    const path = file.source_path || '';
    if (!path) return;

    // 移除开头的斜杠并标准化路径
    const normalizedPath = path.replace(/^\/+/, '');

    // 检查是否在目标目录下
    if (normalizedPath.startsWith(targetPrefix)) {
      // 获取相对路径
      const relativePath = normalizedPath.substring(targetPrefix.length);
      if (!relativePath) return;

      const parts = relativePath.split(/[/\\]/).filter(Boolean);

      if (parts.length === 1) {
        // 直接文件
        files.push({
          ...file,
          fileName: parts[0]
        });
      } else if (parts.length > 1) {
        // 子目录
        directories.add(parts[0]);
      }
    }
  });

  // 添加目录项
  directories.forEach(dirName => {
    const childPath = targetPath === '/' ? `/${dirName}` : `${targetPath}/${dirName}`;
    const key = `dir-${childPath}`;
    keyToPathMap.value.set(key, childPath);

    children.push({
      key,
      label: dirName,
      prefix: () => h('span', { class: 'mr-1' }, '📁'),
      isLeaf: false
      // 不设置 children 属性，让 Naive UI 自动处理懒加载
    });
  });

  // 添加文件项
  files.forEach(file => {
    children.push({
      key: `file-${file.source_path}`,
      label: file.fileName,
      isLeaf: true,
      prefix: () => getNodeIcon({ file, type: 'file' }),
      suffix: () => getNodeSuffix({ file, type: 'file' })
    });
  });

  console.log('从本地数据加载完成:', { directories: directories.size, files: files.length, children: children.length });

  return children;
};

// 为懒加载项目获取图标
const getNodeIconForItem = (item: any, isFile: boolean) => {
  if (!isFile) {
    return h('span', { class: 'mr-1' }, '📁');
  }

  const fileName = item.file_name || item.name || '';
  const ext = getFileExtension(fileName);
  const iconMap: Record<string, string> = {
    'mp4': '🎬', 'avi': '🎬', 'mkv': '🎬', 'mov': '🎬', 'wmv': '🎬',
    'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'aac': '🎵',
    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
    'txt': '📄', 'pdf': '📕', 'doc': '📘', 'docx': '📘',
    'zip': '📦', 'rar': '📦', '7z': '📦'
  };

  const emoji = iconMap[ext] || '📄';
  return h('span', { class: 'mr-1' }, emoji);
};

// 为懒加载项目获取后缀
const getNodeSuffixForItem = (item: any, isFile: boolean) => {
  if (!isFile) return null;

  const elements = [];

  // 文件状态标签
  if (item.is_success === true) {
    elements.push(
      h(NTag, {
        size: 'small',
        type: 'success',
        class: 'ml-2'
      }, { default: () => '✅' })
    );
  } else if (item.is_success === false) {
    elements.push(
      h(NTag, {
        size: 'small',
        type: 'error',
        class: 'ml-2'
      }, { default: () => '❌' })
    );
  }

  // 文件大小
  if (item.file_size || item.size) {
    elements.push(
      h('span', {
        class: 'ml-2 text-xs text-secondary-text'
      }, formatFileSize(item.file_size || item.size))
    );
  }

  return elements.length > 0 ? h('div', { class: 'flex items-center' }, elements) : null;
};

// 构建树形数据结构
const buildTreeData = async () => {
  console.log('buildTreeData 调用', {
    useLazyLoad: props.useLazyLoad,
    taskId: props.taskId,
    filesLength: props.files?.length || 0
  });

  if (props.useLazyLoad) {
    // 懒加载模式：构建根目录结构
    await buildLazyTreeData();
  } else {
    // 传统模式：构建完整树结构
    buildFullTreeData();
  }
};

// 构建懒加载树结构
const buildLazyTreeData = async () => {
  console.log('buildLazyTreeData 开始执行', { taskId: props.taskId });

  if (!props.taskId) {
    console.warn('懒加载模式需要 taskId，当前 taskId:', props.taskId);
    treeData.value = [];
    return;
  }

  try {
    console.log('开始调用 getTaskDirectoryContent API，taskId:', props.taskId);

    // 直接调用 API 获取根目录内容
    const { data } = await getTaskDirectoryContent(props.taskId, {
      directoryPath: '/'
    });

    console.log('API 响应数据:', data);

    const rootNodes: TreeOption[] = [];

    if (data && data.items) {
      console.log('处理 API 返回的 items，数量:', data.items.length);

      data.items.forEach(item => {
        const fileName = item.file_name || item.name;
        const isFile = !item.is_directory;
        const key = `${isFile ? 'file' : 'dir'}-${fileName}`;

        console.log('处理项目:', { fileName, isFile, key });

        if (!isFile) {
          // 记录目录路径映射
          keyToPathMap.value.set(key, `/${fileName}`);
        }

        const nodeConfig: TreeOption = {
          key,
          label: fileName,
          isLeaf: isFile,
          prefix: () => getNodeIconForItem(item, isFile),
          suffix: () => getNodeSuffixForItem(item, isFile)
        };

        // 对于目录，不设置 children 属性，让 Naive UI 自动处理懒加载
        if (isFile) {
          nodeConfig.children = undefined;
        }

        rootNodes.push(nodeConfig);
      });
    } else {
      console.warn('API 返回的数据中没有 items 或 data 为空');
    }

    treeData.value = rootNodes;

    // 默认不展开根节点，等待用户点击
    defaultExpandedKeys.value = [];
    expandedKeys.value = [];

    console.log('懒加载树结构构建完成，根节点数量:', rootNodes.length);
  } catch (error: any) {
    console.error('构建懒加载树结构失败:', error);
    console.error('错误详情:', error.response?.data || error.message);

    // 如果 API 调用失败，回退到使用 props.files 数据
    console.log('回退到使用 props.files 数据，文件数量:', props.files?.length || 0);
    if (props.files && props.files.length > 0) {
      console.log('使用 props.files 构建懒加载树结构');
      buildLazyTreeDataFromFiles();
    } else {
      message.error(`加载根目录失败: ${error.message || '未知错误'}`);
      treeData.value = [];
    }
  }
};

// 从 props.files 构建懒加载树结构（回退方案）
const buildLazyTreeDataFromFiles = () => {
  const rootDirectories = new Set<string>();
  const rootFiles: any[] = [];

  // 分析文件路径，提取根目录和根文件
  props.files.forEach(file => {
    const path = file.source_path || '';
    if (!path) return;

    const parts = path.split(/[/\\]/).filter(Boolean);
    if (parts.length === 1) {
      // 根文件
      rootFiles.push(file);
    } else if (parts.length > 1) {
      // 根目录
      rootDirectories.add(parts[0]);
    }
  });

  // 构建根节点
  const rootNodes: TreeOption[] = [];

  // 添加根目录
  rootDirectories.forEach(dir => {
    const key = `dir-${dir}`;
    keyToPathMap.value.set(key, `/${dir}`);

    rootNodes.push({
      key,
      label: dir,
      prefix: () => h('span', { class: 'mr-1' }, '📁'),
      isLeaf: false
      // 不设置 children 属性，让 Naive UI 自动处理懒加载
    });
  });

  // 添加根文件
  rootFiles.forEach(file => {
    const fileName = file.source_path.split(/[/\\]/).pop() || file.source_path;
    rootNodes.push({
      key: `file-${file.source_path}`,
      label: fileName,
      isLeaf: true,
      prefix: () => getNodeIcon({ file, type: 'file' }),
      suffix: () => getNodeSuffix({ file, type: 'file' })
    });
  });

  treeData.value = rootNodes;

  // 默认不展开根节点，等待用户点击
  defaultExpandedKeys.value = [];
  expandedKeys.value = [];

  console.log('从 props.files 构建懒加载树结构完成，根节点数量:', rootNodes.length);
};

// 构建完整树结构（传统模式）
const buildFullTreeData = () => {
  const tree: Record<string, any> = {};
  const fileMap = new Map<string, any>();

  // 处理每个文件
  props.files.forEach((file, index) => {
    const path = file.source_path || '';
    if (!path) return;

    // 分割路径
    const parts = path.split(/[/\\]/).filter(Boolean);
    let currentLevel = tree;
    let currentPath = '';

    // 构建目录结构
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (!currentLevel[part]) {
        const isFile = i === parts.length - 1;
        const key = `${isFile ? 'file' : 'dir'}-${currentPath}`;

        currentLevel[part] = {
          key,
          label: part,
          isLeaf: isFile,
          children: isFile ? undefined : {},
          path: currentPath,
          file: isFile ? file : null,
          type: isFile ? 'file' : 'directory'
        };

        if (isFile) {
          fileMap.set(key, file);
        }
      }

      if (!currentLevel[part].isLeaf) {
        currentLevel = currentLevel[part].children;
      }
    }
  });

  // 转换为树形数组
  const convertToTreeArray = (obj: any, parentPath = ''): TreeOption[] => {
    return Object.values(obj).map((item: any) => {
      const node: TreeOption = {
        key: item.key,
        label: item.label,
        isLeaf: item.isLeaf,
        prefix: () => getNodeIcon(item),
        suffix: () => getNodeSuffix(item)
      };

      if (!item.isLeaf && item.children) {
        const childrenArray = convertToTreeArray(item.children, item.path);
        if (childrenArray.length > 0) {
          node.children = childrenArray;
        }
      }

      return node;
    });
  };

  treeData.value = convertToTreeArray(tree);

  // 默认展开根目录
  defaultExpandedKeys.value = treeData.value
    .filter(node => !node.isLeaf)
    .map(node => node.key as string);
  expandedKeys.value = [...defaultExpandedKeys.value];
};

// 获取节点图标
const getNodeIcon = (item: any) => {
  if (item.type === 'directory') {
    return h('span', { class: 'mr-1' }, '📁');
  }

  // 文件图标
  const file = item.file;
  if (!file) return h('span', { class: 'mr-1' }, '📄');

  const ext = getFileExtension(file.source_path);
  const iconMap: Record<string, string> = {
    'mp4': '🎬', 'avi': '🎬', 'mkv': '🎬', 'mov': '🎬', 'wmv': '🎬',
    'mp3': '🎵', 'wav': '🎵', 'flac': '🎵', 'aac': '🎵',
    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
    'txt': '📄', 'pdf': '📕', 'doc': '📘', 'docx': '📘',
    'zip': '📦', 'rar': '📦', '7z': '📦'
  };

  const emoji = iconMap[ext] || '📄';
  return h('span', { class: 'mr-1' }, emoji);
};

// 获取节点后缀
const getNodeSuffix = (item: any) => {
  if (item.type === 'file' && item.file) {
    const file = item.file;
    const elements = [];

    // 文件状态标签
    if (file.is_success === true) {
      elements.push(
        h(NTag, {
          size: 'small',
          type: 'success',
          class: 'ml-2'
        }, { default: () => '✅' })
      );
    } else if (file.is_success === false) {
      elements.push(
        h(NTag, {
          size: 'small',
          type: 'error',
          class: 'ml-2'
        }, { default: () => '❌' })
      );
    }

    // 文件大小
    if (file.file_size) {
      elements.push(
        h('span', {
          class: 'ml-2 text-xs text-secondary-text'
        }, formatFileSize(file.file_size))
      );
    }

    return h('div', { class: 'flex items-center' }, elements);
  }

  return null;
};

// 工具函数
const getFileExtension = (path: string): string => {
  if (!path) return '';
  const fileName = path.split('/').pop() || path.split('\\').pop() || path;
  const lastDot = fileName.lastIndexOf('.');
  return lastDot > 0 ? fileName.substring(lastDot + 1).toLowerCase() : '';
};

const formatFileSize = (size: number | string): string => {
  if (!size || size === 0) return '';
  const bytes = typeof size === 'string' ? parseInt(size) : size;
  if (isNaN(bytes)) return '';

  const units = ['B', 'KB', 'MB', 'GB'];
  let index = 0;
  let value = bytes;

  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index++;
  }

  return `${value.toFixed(index === 0 ? 0 : 1)}${units[index]}`;
};

// 事件处理
const handleExpandedKeys = (keys: string[]) => {
  expandedKeys.value = keys;
};

const handleNodeClick = (keys: string[], option: (TreeOption | null)[]) => {
  if (option.length > 0 && option[0]) {
    const node = option[0];
    if (node.isLeaf) {
      // 查找对应的文件数据
      const file = props.files.find(f => {
        const key = `file-${f.source_path}`;
        return key === node.key;
      });
      if (file) {
        emit('fileClick', file);
      }
    }
  }
};

const handleSearch = () => {
  // 搜索时自动展开所有匹配的节点
  if (searchPattern.value) {
    const allKeys = getAllNodeKeys(treeData.value);
    expandedKeys.value = allKeys;
  } else {
    expandedKeys.value = [...defaultExpandedKeys.value];
  }
};

const getAllNodeKeys = (nodes: TreeOption[]): string[] => {
  const keys: string[] = [];
  const traverse = (nodeList: TreeOption[]) => {
    nodeList.forEach(node => {
      if (!node.isLeaf) {
        keys.push(node.key as string);
        if (node.children) {
          traverse(node.children);
        }
      }
    });
  };
  traverse(nodes);
  return keys;
};

// 监听文件变化
watch(() => props.files, async () => {
  if (!props.useLazyLoad) {
    await buildTreeData();
  }
}, { immediate: false });

// 监听懒加载模式变化
watch(() => props.useLazyLoad, async () => {
  await buildTreeData();
}, { immediate: false });

// 监听 taskId 变化
watch(() => props.taskId, async () => {
  if (props.useLazyLoad && props.taskId) {
    await buildTreeData();
  }
}, { immediate: false });

onMounted(async () => {
  await buildTreeData();
});
</script>

<style scoped>
.file-tree-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-height: 200px;
  color: var(--n-text-color-3);
}

.tree-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.tree-search {
  flex-shrink: 0;
}

.text-secondary-text {
  color: var(--n-text-color-3);
}

.mt-2 {
  margin-top: 8px;
}

.mr-1 {
  margin-right: 4px;
}

.ml-2 {
  margin-left: 8px;
}

.text-xs {
  font-size: 12px;
}

.flex {
  display: flex;
}

.items-center {
  align-items: center;
}

/* 树形组件样式调整 */
:deep(.n-tree-node-content) {
  padding: 4px 8px;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

:deep(.n-tree-node-content:hover) {
  background-color: var(--n-hover-color);
}

:deep(.n-tree-node--selected .n-tree-node-content) {
  background-color: var(--n-primary-color-suppl);
}

:deep(.n-tree-node-wrapper) {
  margin: 2px 0;
}
</style>
