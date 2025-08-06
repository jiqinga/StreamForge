import { h } from 'vue';
import { Icon } from '@iconify/vue';

/**
 * 渲染图标
 * 
 * @param icon 图标名称
 * @returns Vue渲染函数
 */
export function renderIcon(icon: string) {
  return () => h(Icon, { icon: `lucide:${icon}` });
} 