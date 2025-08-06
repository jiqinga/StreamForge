<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { Icon } from '@iconify/vue';
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPopconfirm,
  NRadio,
  NRadioGroup,
  NSpace,
  NSpin,
  NTag,
  NTooltip,
  useMessage
} from 'naive-ui';
import {
  createMediaServer,
  deleteMediaServer,
  getMediaServers,
  testServerConnection,
  updateMediaServer
} from '@/service/api/strm';
import { $t } from '@/locales';

// 组件属性定义
defineOptions({ name: 'ServerManagement' });

// 定义属性
const props = defineProps({
  // 是否自动加载服务器列表（默认为true）
  autoLoad: {
    type: Boolean,
    default: true
  },
  // 外部传入的服务器列表（可选）
  externalServers: {
    type: Array,
    default: () => []
  }
});

// 定义事件
const emit = defineEmits(['update:servers']);

// 定义服务器类型接口
interface ServerItem {
  id: number;
  name: string;
  server_type: string;
  base_url: string;
  description?: string;
  auth_required: boolean;
  username?: string;
  password?: string;
  create_time: string;
  status: 'unknown' | 'success' | 'error' | 'warning';
}

// 消息服务
const message = useMessage();

// 加载状态
const loading = ref(false);
const submitting = ref(false);
const testing = ref(false);

// 新服务器测试状态
const newServerTestStatus = ref<'unknown' | 'success' | 'error' | 'warning'>('unknown');

// 服务器列表是否已加载
const serversLoaded = ref(false);

// 辅助函数，获取状态显示
function getStatusType(status: string): 'default' | 'success' | 'error' | 'warning' {
  switch (status) {
    case 'success': return 'success';
    case 'error': return 'error';
    case 'warning': return 'warning';
    default: return 'default';
  }
}

function getStatusIcon(status: string): string {
  switch (status) {
    case 'success': return 'lucide:check-circle';
    case 'error': return 'lucide:x-circle';
    case 'warning': return 'lucide:alert-circle';
    default: return 'lucide:help-circle';
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case 'success': return $t('strm.settings.serverStatusActive' as any) as string;
    case 'error': return $t('strm.settings.serverStatusInactive' as any) as string;
    case 'warning': return $t('strm.settings.serverStatusWarning' as any) as string;
    default: return $t('strm.settings.serverStatusUnknown' as any) as string;
  }
}

// 解码URL，将URL转义字符转回原始显示
function decodeServerUrl(url: string): string {
  try {
    return decodeURIComponent(url);
  } catch {
    return url; // 如果解码失败，返回原始URL
  }
}

// 编码URL，确保发送给后端的URL是正确编码的
function encodeServerUrl(url: string): string {
  try {
    // 检查URL是否已经被编码，避免重复编码
    const decodedUrl = decodeURIComponent(url);
    if (decodedUrl === url) {
      // URL未编码，需要编码
      return encodeURI(url);
    }
    // URL已编码，或者解码与原始URL相同，直接返回原始URL
    return url;
  } catch {
    return url; // 如果处理失败，返回原始URL
  }
}

// 数据
const servers = ref<ServerItem[]>([]);
const showAddModal = ref(false);
const showEditModal = ref(false);

// 表单验证结果
const urlValid = ref(true);
const nameValid = ref(true);

// 表单数据
const formData = reactive({
  id: null as number | null,
  name: '',
  server_type: 'cd2host', // 默认为下载服务器
  base_url: '',
  description: '',
  auth_required: false,
  username: '',
  password: ''
});

// 验证服务器URL
function validateServerUrl(url: string): boolean {
  if (!url || url.trim() === '') {
    return false;
  }

  // 使用更严格的URL验证
  try {
    // 如果不是完整URL，添加协议前缀再尝试
    let testUrl = url;
    if (!url.match(/^https?:\/\//i)) {
      // 添加http前缀以便URL构造函数可以正确解析
      testUrl = `http://${url}`;
    }

    // 尝试创建URL对象以验证URL格式
    const urlObj = new URL(testUrl);

    // 确保URL有效：至少包含域名部分
    return Boolean(urlObj.hostname) && urlObj.hostname.includes('.');
  } catch {
    // 捕获任何解析错误并返回false
    return false;
  }
}

// 验证服务器名称
function validateServerName(name: string): boolean {
  return Boolean(name && name.trim() !== '');
}

// 监视URL输入，实时验证
function handleUrlInput() {
  // 实时验证URL
  urlValid.value = validateServerUrl(formData.base_url);
}

// 监视名称输入，实时验证
function handleNameInput() {
  // 实时验证名称
  nameValid.value = validateServerName(formData.name);
}

// 获取服务器列表
async function fetchServers() {
  try {
    loading.value = true;

    // 检查是否有外部传入的服务器列表
    if (props.externalServers && props.externalServers.length > 0) {
      // 使用外部传入的服务器列表
      servers.value = props.externalServers.map((server: any) => ({
        id: server.id,
        name: server.name,
        server_type: server.server_type,
        base_url: server.base_url,
        description: server.description,
        auth_required: server.auth_required,
        username: server.username,
        password: server.password,
        create_time: server.create_time,
        status: server.status || 'unknown'
      }));

      // 标记服务器列表已加载
      serversLoaded.value = true;
    } else {
      // 没有外部数据源时，从API获取数据
      const res = await getMediaServers();

      if (res.data && Array.isArray(res.data)) {
        // 转换数据
        servers.value = res.data.map((server: any) => {
          return {
            id: server.id,
            name: server.name,
            server_type: server.server_type,
            base_url: server.base_url,
            description: server.description,
            auth_required: server.auth_required,
            username: server.username,
            password: server.password,
            create_time: server.create_time,
            status: server.status || 'unknown' // 使用API返回的status，如果不存在则默认为unknown
          };
        });

        // 标记服务器列表已加载
        serversLoaded.value = true;

        // 向父组件发送服务器列表更新事件
        emit('update:servers');
      } else {
        message.error('服务器数据格式无效');
      }
    }
  } catch (error: any) {
    message.error(error.message || '获取服务器列表失败');
  } finally {
    loading.value = false;
  }
}

// 刷新服务器列表 - 无论是否有外部数据源都强制从API获取
async function refreshServerList() {
  try {
    loading.value = true;

    // 即使有外部数据源，也强制从API获取最新数据
    const res = await getMediaServers();

    if (res.data && Array.isArray(res.data)) {
      // 转换数据
      servers.value = res.data.map((server: any) => {
        return {
          id: server.id,
          name: server.name,
          server_type: server.server_type,
          base_url: server.base_url,
          description: server.description,
          auth_required: server.auth_required,
          username: server.username,
          password: server.password,
          create_time: server.create_time,
          status: server.status || 'unknown'
        };
      });

      // 标记服务器列表已加载
      serversLoaded.value = true;

      // 向父组件发送服务器列表更新事件
      emit('update:servers');
    } else {
      message.error('服务器数据格式无效');
    }
  } catch (error: any) {
    message.error(error.message || '获取服务器列表失败');
  } finally {
    loading.value = false;
  }
}

// 添加服务器
function handleAdd() {
  // 重置表单
  Object.assign(formData, {
    id: null,
    name: '',
    server_type: 'cd2host', // 默认为下载服务器
    base_url: '',
    description: '',
    auth_required: false,
    username: '',
    password: ''
  });
  urlValid.value = true;  // 重置验证状态
  nameValid.value = true;  // 重置名称验证状态
  newServerTestStatus.value = 'unknown';  // 重置测试状态
  showAddModal.value = true;
}

// 编辑服务器
function handleEdit(row: ServerItem) {
  // 填充表单，并解码URL
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    server_type: row.server_type,
    base_url: decodeServerUrl(row.base_url),
    description: row.description || '',
    auth_required: row.auth_required,
    username: row.username || '',
    password: ''  // 不显示密码
  });
  urlValid.value = validateServerUrl(formData.base_url);  // 初始验证已解码的URL
  nameValid.value = validateServerName(row.name);  // 初始验证名称
  newServerTestStatus.value = row.status;  // 设置测试状态为当前服务器状态
  showEditModal.value = true;
}

// 测试服务器连接
async function handleTestConnection(serverId: number) {
  try {
    testing.value = true;

    // 查找服务器索引
    const serverIndex = servers.value.findIndex(s => s.id === serverId);
    if (serverIndex === -1) {
      message.error('找不到指定的服务器');
      return;
    }

    // 创建服务器对象的副本，避免直接修改数组中的对象
    const serversCopy = [...servers.value];
    serversCopy[serverIndex] = {
      ...serversCopy[serverIndex],
      status: 'unknown'
    };

    // 更新状态为测试中
    servers.value = serversCopy;

    // 发送测试请求
    const res = await testServerConnection(serverId);

    // 再次创建服务器对象的副本
    const updatedServersCopy = [...servers.value];

    // 更新服务器状态
    if (res.data && res.data.status) {
      updatedServersCopy[serverIndex] = {
        ...updatedServersCopy[serverIndex],
        status: res.data.status as 'success' | 'error' | 'warning'
      };
      servers.value = updatedServersCopy;
      message.success(res.data.message || '连接测试完成');
    } else {
      updatedServersCopy[serverIndex] = {
        ...updatedServersCopy[serverIndex],
        status: 'error'
      };
      servers.value = updatedServersCopy;
      message.error(res.data?.message || '连接测试失败');
    }
  } catch (error: any) {
    message.error(error.message || '测试连接失败');
  } finally {
    testing.value = false;
  }
}

// 测试添加的服务器连接
async function handleTestNewServer() {
  // 验证URL
  if (!urlValid.value || !formData.base_url) {
    message.error('请输入有效的服务器地址');
    return;
  }

  try {
    testing.value = true;
    // 重置测试状态
    newServerTestStatus.value = 'unknown';

    // 编码URL后再发送给后端
    const encodedUrl = encodeServerUrl(formData.base_url);

    // 构造临时服务器对象用于测试
    const tempServer = {
      name: formData.name || '未命名服务器', // 使用固定的名称替代国际化键
      server_type: formData.server_type,
      base_url: encodedUrl, // 使用编码后的URL
      description: formData.description || null,
      auth_required: false,  // 固定为false
      username: null,
      password: null
    };

    // 发送测试请求
    const res = await testServerConnection(0, tempServer);

    // 使用局部变量存储状态，避免响应式变量的多次更新
    let status: 'unknown' | 'success' | 'error' | 'warning' = 'unknown';

    if (res.data && res.data.status) {
      status = res.data.status as 'success' | 'error' | 'warning';

      if (status === 'success') {
        message.success(res.data.message || '测试成功');
      } else if (status === 'error') {
        message.error(res.data.message || '测试失败');
      } else {
        message.warning(res.data.message || '测试结果不确定');
      }
    } else if (res.data && res.data.message) {
      status = 'error';
      message.error(res.data.message);
    } else {
      status = 'error';
      message.error('测试失败，请检查服务器地址');
    }

    // 测试完成后一次性更新状态
    newServerTestStatus.value = status;
  } catch (error: any) {
    newServerTestStatus.value = 'error';
    if (error.response && error.response.data && error.response.data.msg) {
      message.error(`测试失败: ${error.response.data.msg}`);
    } else {
      message.error(error.message || '测试失败');
    }
  } finally {
    testing.value = false;
  }
}

// 删除服务器
async function handleDelete(id: number) {
  try {
    // 添加删除前的警告提示
    const server = servers.value.find(s => s.id === id);
    if (!server) {
      message.error('找不到指定的服务器');
      return;
    }

    // 先删除服务器
    await deleteMediaServer(id);
    message.success('删除成功');

    // 立即刷新服务器列表
    await refreshServerList();

    // 如果是在系统设置页面删除的服务器，提示用户可能需要检查系统设置
    message.info('服务器已删除，如果该服务器曾被设置为默认服务器，系统已自动解除关联');
  } catch (error: any) {
    message.error(error.message || '删除失败');
  }
}

// 保存服务器
async function handleSave(isNew = false) {
  try {
    // 验证服务器名称
    nameValid.value = validateServerName(formData.name);
    if (!nameValid.value) {
      message.error('请输入服务器名称');
      return;
    }

    // 验证服务器URL
    if (!urlValid.value || !formData.base_url) {
      message.error('请输入有效的服务器地址');
      return;
    }

    submitting.value = true;

    // 将表单中的URL编码后再发送给后端
    const encodedUrl = encodeServerUrl(formData.base_url);

    // 构造请求数据
    const data = {
      name: formData.name,
      server_type: formData.server_type,
      base_url: encodedUrl, // 使用编码后的URL发送给后端
      description: formData.description || null,
      auth_required: false,  // 固定为false，移除认证需求
      username: null,
      password: null,
      status: newServerTestStatus.value  // 包含测试状态
    };

    if (isNew) {
      // 新增
      await createMediaServer(data);
      message.success('添加成功');

      // 先关闭模态框
      showAddModal.value = false;

      // 立即刷新服务器列表
      await refreshServerList();

      // 提示用户服务器列表已更新
      message.info('服务器列表已更新');
    } else if (formData.id !== null) {
      // 更新
      await updateMediaServer(formData.id, data);
      message.success('更新成功');

      // 先关闭模态框
      showEditModal.value = false;

      // 立即刷新服务器列表
      await refreshServerList();

      // 提示用户服务器列表已更新
      message.info('服务器列表已更新');
    }

    // 重置测试状态
    newServerTestStatus.value = 'unknown';
  } catch (error: any) {
    message.error(error.message || (isNew ? '添加失败' : '更新失败'));
  } finally {
    submitting.value = false;
  }
}

// 清理资源的函数
function cleanup() {
  // 重置所有状态
  servers.value = [];
  loading.value = false;
  submitting.value = false;
  testing.value = false;
  showAddModal.value = false;
  showEditModal.value = false;
  urlValid.value = true;
  nameValid.value = true;
  newServerTestStatus.value = 'unknown';
}

// 监听外部服务器列表变化
watch(() => props.externalServers, (newServers) => {
  if (newServers && newServers.length > 0) {
    // 当外部服务器列表变化且不为空时，更新本地服务器列表
    servers.value = newServers.map((server: any) => ({
      id: server.id,
      name: server.name,
      server_type: server.server_type,
      base_url: server.base_url,
      description: server.description,
      auth_required: server.auth_required,
      username: server.username,
      password: server.password,
      create_time: server.create_time,
      status: server.status || 'unknown'
    }));

    // 标记服务器列表已加载，避免重复加载
    serversLoaded.value = true;
  }
}, { deep: true, immediate: true });

// 生命周期
onMounted(() => {
  // 已经有外部数据时，跳过加载过程
  if (props.externalServers && props.externalServers.length > 0) {
    // 如果有外部传入的数据，标记为已加载，不进行任何网络请求
    serversLoaded.value = true;
    return;
  }

  // 只有在设置了自动加载属性时，且外部未传入服务器列表时才自动加载服务器列表
  if (props.autoLoad) {
    fetchServers().then(() => {
      serversLoaded.value = true;
    });
  }
});

// 组件卸载前清理资源
onBeforeUnmount(() => {
  cleanup();
});
</script>

<template>
  <div>
    <div class="server-management">
      <div class="mb-4 flex justify-between items-center">
        <h3 class="text-lg font-bold">{{ $t('strm.settings.serverManagement') }}</h3>
        <n-button type="primary" size="small" @click="handleAdd">
          <template #icon>
            <Icon icon="lucide:plus" />
          </template>
          {{ $t('strm.settings.addServer') }}
        </n-button>
      </div>

      <n-spin :show="loading">
        <div class="table-wrapper">
          <table class="full-width-table">
            <thead>
              <tr>
                <th width="15%">{{ $t('strm.settings.serverName') }}</th>
                <th width="20%">{{ $t('strm.settings.serverType') }}</th>
                <th width="35%">URL</th>
                <th width="15%">{{ $t('strm.settings.status') }}</th>
                <th width="15%">{{ $t('common.action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="server in servers" :key="`server-${server.id}`">
                <td>{{ server.name }}</td>
                <td>
                  <n-tag :type="server.server_type === 'xiaoyahost' ? 'success' : 'warning'" round size="small">
                    <template #icon>
                      <Icon
                        :icon="server.server_type === 'xiaoyahost' ? 'material-symbols:smart-display' : 'material-symbols:download'"
                        class="mr-1" />
                    </template>
                    {{ server.server_type === 'xiaoyahost' ? $t('strm.settings.mediaServer') :
                      $t('strm.settings.downloadServer') }}
                  </n-tag>
                </td>
                <td class="url-cell">
                  <div class="flex justify-center">
                    <n-tooltip trigger="hover" placement="top" style="max-width: 90%">
                      <template #trigger>
                        <div class="truncate">{{ decodeServerUrl(server.base_url) }}</div>
                      </template>
                      {{ decodeServerUrl(server.base_url) }}
                    </n-tooltip>
                  </div>
                </td>
                <td>
                  <n-tag :type="getStatusType(server.status)" round size="small">
                    <template #icon>
                      <Icon :icon="getStatusIcon(server.status)" class="mr-1" />
                    </template>
                    {{ getStatusText(server.status) }}
                  </n-tag>
                </td>
                <td>
                  <div class="flex justify-center gap-2">
                    <!-- 测试按钮 -->
                    <n-button size="small" @click="handleTestConnection(server.id)" type="info" quaternary circle
                      title="测试连接">
                      <template #icon>
                        <Icon icon="lucide:activity" />
                      </template>
                    </n-button>

                    <!-- 编辑按钮 -->
                    <n-button size="small" @click="handleEdit(server)" type="primary" quaternary circle title="编辑">
                      <template #icon>
                        <Icon icon="lucide:edit" />
                      </template>
                    </n-button>

                    <!-- 删除按钮 -->
                    <n-popconfirm @positive-click="handleDelete(server.id)" :negative-text="$t('strm.settings.cancel')"
                      :positive-text="$t('strm.settings.confirm')">
                      <template #trigger>
                        <n-button size="small" type="error" quaternary circle title="删除">
                          <template #icon>
                            <Icon icon="lucide:trash-2" />
                          </template>
                        </n-button>
                      </template>
                      {{ $t('strm.settings.confirmDelete') }}
                    </n-popconfirm>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="servers.length === 0 && !loading" class="empty-state">
          <Icon icon="lucide:database" class="empty-icon" />
          <p>{{ $t('strm.settings.noServers') }}</p>
        </div>
      </n-spin>
    </div>

    <!-- 添加服务器 -->
    <n-modal v-model:show="showAddModal" :title="$t('strm.settings.addServer')" preset="card" :mask-closable="false"
      style="width: 500px">
      <n-form :model="formData" label-placement="left" label-width="auto" require-mark-placement="right-hanging">
        <n-form-item :label="$t('strm.settings.serverName')" required>
          <n-input v-model:value="formData.name" @input="handleNameInput"
            :placeholder="$t('strm.settings.serverNamePlaceholder')" />
          <template #feedback v-if="!nameValid">
            <span class="text-error text-sm">请输入服务器名称</span>
          </template>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.serverType')" required>
          <div class="server-type-selector">
            <n-radio-group v-model:value="formData.server_type" name="server-type-group">
              <n-space>
                <n-radio value="cd2host">
                  <div class="radio-label">
                    <Icon icon="material-symbols:download" class="server-type-icon download" />
                    <span>{{ $t('strm.settings.downloadServer') }}</span>
                  </div>
                </n-radio>
                <n-radio value="xiaoyahost">
                  <div class="radio-label">
                    <Icon icon="material-symbols:smart-display" class="server-type-icon media" />
                    <span>{{ $t('strm.settings.mediaServer') }}</span>
                  </div>
                </n-radio>
              </n-space>
            </n-radio-group>
          </div>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.baseUrl')" required>
          <n-input v-model:value="formData.base_url" @input="handleUrlInput"
            :placeholder="$t('strm.settings.baseUrlPlaceholder')" />
          <template #feedback v-if="!urlValid">
            <span class="text-error text-sm">请输入有效的服务器地址 (例如: example.com)</span>
          </template>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.description')">
          <n-input v-model:value="formData.description" type="textarea"
            :placeholder="$t('strm.settings.descriptionPlaceholder')" />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="flex justify-between items-center">
          <n-button type="info" :loading="testing" @click="handleTestNewServer"
            :disabled="!urlValid || !formData.base_url">
            <template #icon>
              <Icon icon="lucide:activity" />
            </template>
            {{ $t('strm.settings.test') }}
          </n-button>

          <div class="space-x-2">
            <n-button @click="showAddModal = false">{{ $t('strm.settings.cancel') }}</n-button>
            <n-button type="primary" :loading="submitting" @click="handleSave(true)"
              :disabled="!nameValid || !urlValid || !formData.name || !formData.base_url">
              {{ $t('strm.settings.save') }}
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>

    <!-- 编辑服务器 -->
    <n-modal v-model:show="showEditModal" :title="$t('strm.settings.editServer')" preset="card" :mask-closable="false"
      style="width: 500px">
      <n-form :model="formData" label-placement="left" label-width="auto" require-mark-placement="right-hanging">
        <n-form-item :label="$t('strm.settings.serverName')" required>
          <n-input v-model:value="formData.name" @input="handleNameInput"
            :placeholder="$t('strm.settings.serverNamePlaceholder')" />
          <template #feedback v-if="!nameValid">
            <span class="text-error text-sm">请输入服务器名称</span>
          </template>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.serverType')" required>
          <div class="server-type-selector">
            <n-radio-group v-model:value="formData.server_type" name="server-type-group-edit">
              <n-space>
                <n-radio value="cd2host">
                  <div class="radio-label">
                    <Icon icon="material-symbols:download" class="server-type-icon download" />
                    <span>{{ $t('strm.settings.downloadServer') }}</span>
                  </div>
                </n-radio>
                <n-radio value="xiaoyahost">
                  <div class="radio-label">
                    <Icon icon="material-symbols:smart-display" class="server-type-icon media" />
                    <span>{{ $t('strm.settings.mediaServer') }}</span>
                  </div>
                </n-radio>
              </n-space>
            </n-radio-group>
          </div>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.baseUrl')" required>
          <n-input v-model:value="formData.base_url" @input="handleUrlInput"
            :placeholder="$t('strm.settings.baseUrlPlaceholder')" />
          <template #feedback v-if="!urlValid">
            <span class="text-error text-sm">请输入有效的服务器地址 (例如: example.com)</span>
          </template>
        </n-form-item>

        <n-form-item :label="$t('strm.settings.description')">
          <n-input v-model:value="formData.description" type="textarea"
            :placeholder="$t('strm.settings.descriptionPlaceholder')" />
        </n-form-item>
      </n-form>

      <template #footer>
        <div class="flex justify-between items-center">
          <n-button type="info" :loading="testing" @click="handleTestNewServer"
            :disabled="!urlValid || !formData.base_url">
            <template #icon>
              <Icon icon="lucide:activity" />
            </template>
            {{ $t('strm.settings.test') }}
          </n-button>

          <div class="space-x-2">
            <n-button @click="showEditModal = false">{{ $t('strm.settings.cancel') }}</n-button>
            <n-button type="primary" :loading="submitting" @click="handleSave(false)"
              :disabled="!nameValid || !urlValid || !formData.name || !formData.base_url">
              {{ $t('strm.settings.save') }}
            </n-button>
          </div>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.server-management {
  width: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

/* 表格容器 */
.table-wrapper {
  width: 100%;
  margin-left: -120px;
  /* 向左偏移抵消多余空白 */
  padding-left: 120px;
  /* 内部填充，确保内容正确对齐 */
  border-radius: 8px;
  overflow: hidden;
  background-color: white;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

/* 表格样式 */
.full-width-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  margin: 0;
  padding: 0;
  border: none;
}

.full-width-table th {
  background-color: #f5f7fa;
  font-weight: 600;
  padding: 12px 8px;
  text-align: center;
  border-bottom: 1px solid #eaeaea;
}

.full-width-table td {
  padding: 12px 8px;
  border-bottom: 1px solid #f0f0f0;
  text-align: center;
  vertical-align: middle;
}

.full-width-table tr:nth-child(even) {
  background-color: #f9fafb;
}

.full-width-table tr:hover {
  background-color: #f0f7ff;
}

/* URL单元格样式 */
.url-cell {
  overflow: hidden;
}

.url-cell .flex {
  display: flex;
  justify-content: center;
  width: 100%;
}

.url-cell .truncate {
  max-width: 95%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: inline-block;
}

/* 服务器类型单选按钮样式 */
.server-type-selector {
  margin: 8px 0;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-type-icon {
  font-size: 16px;
}

.server-type-icon.download {
  color: #1890ff;
}

.server-type-icon.media {
  color: #52b54b;
}

.text-error {
  color: var(--error-color, #f56c6c);
}
</style>
