<script setup lang="ts">
import { computed, reactive } from 'vue';
import { $t } from '@/locales';
import { useRouterPush } from '@/hooks/common/router';
import { useFormRules, useNaiveForm } from '@/hooks/common/form';
import { useCaptcha } from '@/hooks/business/captcha';
import { fetchSendResetCode, fetchResetPassword } from '@/service/api/auth';

defineOptions({
  name: 'ResetPwd'
});

const { toggleLoginModule } = useRouterPush();
const { formRef, validate } = useNaiveForm();
const { label, isCounting, loading, getCaptcha } = useCaptcha();

interface FormModel {
  email: string;
  code: string;
  password: string;
  confirmPassword: string;
}

const model: FormModel = reactive({
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
});

type RuleRecord = Partial<Record<keyof FormModel, App.Global.FormRule[]>>;

const rules = computed<RuleRecord>(() => {
  const { formRules, createConfirmPwdRule } = useFormRules();

  return {
    email: formRules.email,
    code: formRules.code,
    password: formRules.pwd,
    confirmPassword: createConfirmPwdRule(model.password)
  };
});

async function handleSendCode() {
  if (!model.email) {
    window.$message?.warning($t('page.login.common.emailRequired'));
    return;
  }

  try {
    await fetchSendResetCode(model.email);
    getCaptcha(model.email);
    window.$message?.success($t('page.login.resetPwd.codeSent'));
  } catch (error) {
    window.$message?.error($t('page.login.resetPwd.sendCodeFailed'));
  }
}

async function handleSubmit() {
  await validate();

  try {
    const res = await fetchResetPassword(model.email, model.code, model.password);
    if (res.code === "0000") {
      window.$message?.success(res.msg || $t('page.login.resetPwd.resetSuccess'));
      // 重置成功后跳转到登录页面
      toggleLoginModule('pwd-login');
    } else {
      window.$message?.error(res.msg || $t('page.login.resetPwd.resetFailed'));
    }
  } catch (error) {
    window.$message?.error($t('page.login.resetPwd.resetFailed'));
  }
}
</script>

<template>
  <NForm ref="formRef" :model="model" :rules="rules" size="large" :show-label="false" @keyup.enter="handleSubmit">
    <NFormItem path="email">
      <NInput v-model:value="model.email" :placeholder="$t('page.login.common.emailPlaceholder')" />
    </NFormItem>
    <NFormItem path="code">
      <div class="w-full flex-y-center gap-16px">
        <NInput v-model:value="model.code" :placeholder="$t('page.login.common.codePlaceholder')" />
        <NButton size="large" :disabled="isCounting" :loading="loading" @click="handleSendCode">
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
