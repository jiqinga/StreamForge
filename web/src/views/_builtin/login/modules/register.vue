<script setup lang="ts">
import { computed, reactive } from 'vue';
import { $t } from '@/locales';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { useCaptcha } from '@/hooks/business/captcha';
import { fetchRegister } from '@/service/api/auth';

defineOptions({
  name: 'Register'
});

const { toggleLoginModule } = useRouterPush();
const { formRef, validate } = useNaiveForm();
const { label, isCounting, loading, getCaptcha } = useCaptcha();

interface FormModel {
  userName: string;
  code: string;
  password: string;
  confirmPassword: string;
  email?: string;
}

const model: FormModel = reactive({
  userName: '',
  code: '',
  password: '',
  confirmPassword: '',
  email: ''
});

const rules = computed<Record<keyof FormModel, App.Global.FormRule[]>>(() => {
  const { formRules, createConfirmPwdRule } = useFormRules();

  return {
    userName: formRules.username,
    code: formRules.code,
    password: formRules.pwd,
    confirmPassword: createConfirmPwdRule(model.password),
    email: formRules.email
  };
});

async function handleSubmit() {
  await validate();

  // 调用注册API
  try {
    const res = await fetchRegister(model.userName, model.password, model.email);
    if (res.code === "0000") {
      window.$message?.success(res.msg || $t('page.login.common.validateSuccess'));
      // 注册成功后跳转到登录页面
      toggleLoginModule('pwd-login');
    } else {
      window.$message?.error(res.msg || $t('page.login.common.validateError'));
    }
  } catch (error) {
    window.$message?.error($t('page.login.common.validateError'));
  }
}
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NFormItem path="userName">
      <NInput v-model:value="model.userName" :placeholder="$t('page.login.common.usernamePlaceholder')" />
    </NFormItem>
    <NFormItem path="email">
      <NInput v-model:value="model.email" :placeholder="$t('page.login.common.emailPlaceholder')" />
    </NFormItem>
    <NFormItem path="code">
      <div class="w-full flex-y-center gap-16px">
        <NInput v-model:value="model.code" :placeholder="$t('page.login.common.codePlaceholder')" />
        <NButton size="large" :disabled="isCounting" :loading="loading" @click="getCaptcha(model.email)">
          {{ label }}
        </NButton>
      </div>
    </NFormItem>
    <NFormItem path="password">
      <NInput
        v-model:value="model.password"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.passwordPlaceholder')"
      />
    </NFormItem>
    <NFormItem path="confirmPassword">
      <NInput
        v-model:value="model.confirmPassword"
        type="password"
        show-password-on="click"
        :placeholder="$t('page.login.common.confirmPasswordPlaceholder')"
      />
    </NFormItem>
    <NSpace vertical :size="18" class="w-full">
      <NButton type="primary" size="large" round block @click="handleSubmit">
        {{ $t('common.confirm') }}
      </NButton>
      <NButton size="large" round block @click="toggleLoginModule('pwd-login')">
        {{ $t('page.login.common.back') }}
      </NButton>
    </NSpace>
  </NForm>
</template>

<style scoped></style>
