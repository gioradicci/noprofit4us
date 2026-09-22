<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../supabase'
import { useRouter } from 'vue-router'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import { useI18n } from 'vue-i18n'
import { useUser } from '../composables/useUser'

const { t } = useI18n()
const router = useRouter()
const { isPasswordRecovery } = useUser()

// State
const mode = ref('request') // 'request' | 'sent' | 'newPassword'
const email = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref(false)

onMounted(async () => {
  // Ascolta cambi di stato auth (es. se la sessione viene recuperata asincronamente dall'hash URL)
  supabase.auth.onAuthStateChange((event, session) => {
    if (session || event === 'PASSWORD_RECOVERY') {
      isPasswordRecovery.value = true
      mode.value = 'newPassword'
    }
  })

  // Controlla se la sessione Supabase è già stata creata dal magic link
  const { data: { session } } = await supabase.auth.getSession()

  const isHashRecovery = typeof window !== 'undefined' && (
    window.location.hash.includes('type=recovery') ||
    window.location.search.includes('type=recovery')
  )

  if (session || isPasswordRecovery.value || isHashRecovery) {
    isPasswordRecovery.value = true
    mode.value = 'newPassword'
  } else {
    mode.value = 'request'
  }
})

async function sendResetEmail() {
  error.value = ''
  loading.value = true

  const FRONTEND_URL = (typeof window !== 'undefined' ? window.location.origin : (import.meta.env.VITE_FRONTEND_URL || '')).replace(/\/+$/, '')

  const { error: resetError } = await supabase.auth.resetPasswordForEmail(email.value, {
    redirectTo: `${FRONTEND_URL}/reset-password`
  })

  loading.value = false

  if (resetError) {
    error.value = resetError.message
  } else {
    mode.value = 'sent'
  }
}

async function updatePassword() {
  error.value = ''

  // Validation
  if (newPassword.value.length < 6) {
    error.value = t('home.resetPassword.errorMinLength')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = t('home.resetPassword.errorMismatch')
    return
  }

  loading.value = true

  const { error: updateError } = await supabase.auth.updateUser({
    password: newPassword.value
  })

  loading.value = false

  if (updateError) {
    error.value = updateError.message
  } else {
    success.value = true
    isPasswordRecovery.value = false
    setTimeout(() => {
      router.push('/')
    }, 2500)
  }
}

function goToLogin() {
  isPasswordRecovery.value = false
  router.push('/')
}
</script>

<template>
  <div class="reset-container py-5 px-2">
    <div class="flex justify-content-center">
      <div class="card reset-card p-5 shadow-3 border-round-xl surface-card max-w-25rem w-full">

        <!-- MODE: Request reset email -->
        <template v-if="mode === 'request'">
          <div class="text-center mb-4">
            <i class="pi pi-lock text-5xl text-primary mb-3 block"></i>
            <h2 class="text-2xl font-bold mb-2 mt-0">{{ t('home.resetPassword.title') }}</h2>
            <p class="text-color-secondary text-sm line-height-3 m-0">{{ t('home.resetPassword.description') }}</p>
          </div>

          <form class="flex flex-column gap-3" @submit.prevent="sendResetEmail">
            <InputText
              v-model="email"
              :placeholder="t('home.resetPassword.emailPlaceholder')"
              type="email"
              class="w-full"
              id="reset-email"
              autocomplete="email"
              required
            />

            <small v-if="error" class="p-error text-center" style="color: red;">{{ error }}</small>

            <Button
              :label="loading ? t('home.resetPassword.sending') : t('home.resetPassword.sendLink')"
              :loading="loading"
              type="submit"
              class="w-full"
              icon="pi pi-envelope"
            />

            <Button
              :label="t('home.resetPassword.backToLogin')"
              link
              class="w-full p-0 text-sm"
              @click="goToLogin"
              icon="pi pi-arrow-left"
            />
          </form>
        </template>

        <!-- MODE: Email sent successfully -->
        <template v-else-if="mode === 'sent'">
          <div class="text-center">
            <i class="pi pi-check-circle text-5xl text-green-500 mb-3 block"></i>
            <h2 class="text-2xl font-bold mb-2 mt-0">{{ t('home.resetPassword.successTitle') }}</h2>
            <p class="text-color-secondary text-sm line-height-3 mb-4">{{ t('home.resetPassword.successDesc') }}</p>

            <Button
              :label="t('home.resetPassword.backToLogin')"
              class="w-full"
              @click="goToLogin"
              icon="pi pi-arrow-left"
              severity="secondary"
              outlined
            />
          </div>
        </template>

        <!-- MODE: Set new password -->
        <template v-else-if="mode === 'newPassword'">
          <div class="text-center mb-4">
            <i class="pi pi-key text-5xl text-primary mb-3 block"></i>
            <h2 class="text-2xl font-bold mb-2 mt-0">{{ t('home.resetPassword.newPasswordTitle') }}</h2>
            <p class="text-color-secondary text-sm line-height-3 m-0">{{ t('home.resetPassword.newPasswordDesc') }}</p>
          </div>

          <!-- Success message after update -->
          <div v-if="success" class="text-center">
            <i class="pi pi-check-circle text-5xl text-green-500 mb-3 block"></i>
            <p class="text-green-500 font-semibold">{{ t('home.resetPassword.passwordUpdated') }}</p>
          </div>

          <form v-else class="flex flex-column gap-3" @submit.prevent="updatePassword">
            <InputText
              v-model="newPassword"
              :placeholder="t('home.resetPassword.newPassword')"
              type="password"
              class="w-full"
              id="new-password"
              autocomplete="new-password"
              required
            />

            <InputText
              v-model="confirmPassword"
              :placeholder="t('home.resetPassword.confirmPassword')"
              type="password"
              class="w-full"
              id="confirm-password"
              autocomplete="new-password"
              required
            />

            <small v-if="error" class="p-error text-center" style="color: red;">{{ error }}</small>

            <Button
              :label="loading ? t('home.resetPassword.updating') : t('home.resetPassword.updatePassword')"
              :loading="loading"
              type="submit"
              class="w-full"
              icon="pi pi-check"
            />
          </form>
        </template>

      </div>
    </div>
  </div>
</template>

<style scoped>
.reset-container {
  max-width: 1020px;
  margin: 0 auto;
}

.reset-card {
  border-top: 3px solid #ea580c;
}
</style>
