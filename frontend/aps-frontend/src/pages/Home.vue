<script setup>
import { API_URL } from '../config.js'
import { ref, onMounted, watch, computed } from 'vue'
import { supabase } from '../supabase'
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const isAuthenticated = ref(false)
const isLoading = ref(true)

const email = ref('')
const password = ref('')
const isRegistering = ref(false)
const authError = ref('')
const authLoading = ref(false)

async function loginWithEmail() {
  authError.value = ''
  authLoading.value = true
  const { data, error } = await supabase.auth.signInWithPassword({
    email: email.value,
    password: password.value
  })
  if (error) authError.value = error.message
  authLoading.value = false
}

async function registerWithEmail() {
  authError.value = ''
  authLoading.value = true
  
 // URL del frontend, prende dall'ambiente Vite
const FRONTEND_URL = import.meta.env.VITE_FRONTEND_URL || window.location.origin
  
  const { data, error } = await supabase.auth.signUp({
    email: email.value,
    password: password.value,
    options: {
      emailRedirectTo: FRONTEND_URL
    }
  })
  
  if (error) authError.value = error.message
  else authError.value = t('home.loginCard.emailCheck')
  authLoading.value = false
}

const backendUser = ref(null)
const loadingBackend = ref(false)
const mese_inizio_rinnovo_anticipato = 10

async function loadUser() {
  if (!isAuthenticated.value) return
  loadingBackend.value = true
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch(API_URL + "/users/me", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      backendUser.value = await res.json()
    }
  } catch (e) {
    console.error("Errore loadUser:", e)
  } finally {
    loadingBackend.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    const activeLocale = locale.value === 'it' ? 'it-IT' : 'en-US'
    return d.toLocaleDateString(activeLocale, { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch (e) {
    return dateStr
  }
}

onMounted(async () => {
  const { data: { session } } = await supabase.auth.getSession()
  isAuthenticated.value = !!session
  isLoading.value = false
  if (isAuthenticated.value) {
    loadUser()
  }

  supabase.auth.onAuthStateChange((event, _session) => {
    isAuthenticated.value = !!_session
    if (isAuthenticated.value) {
      loadUser()
    } else {
      backendUser.value = null
    }
  })
})

const memberTypes = computed(() => [
  { label: t('common.memberTypes.standard'), value: "ORDINARIO" },
  { label: t('common.memberTypes.supporting'), value: "SOSTENITORE" }
])
const selectedMemberType = ref(null)

const paymentMethods = computed(() => [
  { label: t('common.paymentMethods.bankTransfer'), value: "Bonifico Bancario" },
  { label: t('common.paymentMethods.paypal'), value: "PayPal" },
  { label: t('common.paymentMethods.satispay'), value: "Satispay" },
  { label: t('common.paymentMethods.cash'), value: "Contanti" },
  { label: t('common.paymentMethods.pos'), value: "POS" }
])
const selectedPaymentMethod = ref(null)
const renewing = ref(false)

async function requestRenewal() {
  if (!selectedPaymentMethod.value || !selectedMemberType.value) return;
  renewing.value = true;
  try {
    const { data: { session } } = await supabase.auth.getSession()
    const token = session.access_token
    const res = await fetch(API_URL + "/users/me/request-renew", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ payment_method: selectedPaymentMethod.value, member_type: selectedMemberType.value })
    })
    if (res.ok) {
      await loadUser()
    }
  } catch (e) {
    console.error("Errore requestRenewal:", e)
  } finally {
    renewing.value = false;
  }
}

function memberNoActive() {
  let retVal = (!backendUser.value.end_date || new Date(backendUser.value.end_date) < new Date());
  return retVal
};

function memberExpiring() {
  if (memberNoActive()) return false;
  if (!backendUser.value || !backendUser.value.end_date) return false;
  
  const today = new Date();
  const endDate = new Date(backendUser.value.end_date);
  
  if (endDate.getFullYear() === today.getFullYear() && today.getMonth() >= mese_inizio_rinnovo_anticipato) {
    return true;
  }
  return false;
}

function getRenewalYear() {
  if (!backendUser.value || !backendUser.value.end_date) return new Date().getFullYear();
  const endDate = new Date(backendUser.value.end_date);
  const today = new Date();
  if (endDate < today) {
    return today.getFullYear();
  }
  return endDate.getFullYear() + 1;
}

function getRoleIcon() {
  const role = backendUser.value?.role || 'USER';
  const roles = backendUser.value?.roles || [];
  
  if (role === 'ADMIN' || roles.includes('ADMIN')) return 'pi-crown';
  if (role === 'TREASURER' || roles.includes('TREASURER')) return 'pi-money-bill';
  if (role === 'SECRETARY' || roles.includes('SECRETARY')) return 'pi-envelope';
  return 'pi-user';
}
</script>

<template>
  <!-- ⏳ Stato Caricamento -->
  <div v-if="isLoading || (isAuthenticated && loadingBackend)" class="flex flex-column align-items-center justify-content-center min-h-30rem gap-3">
    <i class="pi pi-spin pi-spinner text-4xl text-primary"></i>
    <span class="text-color-secondary text-sm">{{ t('common.loading') }}</span>
  </div>

  <div v-else class="home-container py-5 px-2">

    <!-- 🟢 CASO 1: UTENTE NON LOGGATO -->
    <div v-if="!isAuthenticated">
      
      <!-- Hero Banner -->
      <div class="hero-section text-center py-4 px-4 mb-5 border-round-3xl shadow-1 relative overflow-hidden">
        <div class="mb-3">
          <Image src="/logo.svg" alt="Logo" width="100"></Image>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold mb-3 mt-0 text-primary-gradient">{{ t('home.title') }}</h1>
        <h2 class="text-1xl md:text-2xl font-bold mb-3 mt-0 text-primary-gradient">{{ t('home.demoWarning') }}</h2>
        <p class="text-lg md:text-xl text-color-secondary mb-5 max-w-30rem mx-auto line-height-3">
          {{ t('home.subtitle') }}
        </p>
        
        <div class="card p-4 mx-auto max-w-20rem mt-4 surface-card border-round shadow-2">
          <h3 class="mb-3 mt-0 text-center text-color">{{ isRegistering ? t('home.loginCard.register') : t('home.loginCard.login') }}</h3>
          
          <form class="flex flex-column gap-3">
            <InputText v-model="email" :placeholder="t('home.loginCard.email')" type="email" class="w-full" id="email" autocomplete="on"/>
            <InputText v-model="password" :placeholder="t('home.loginCard.password')" type="password" class="w-full" id="password" autocomplete="off"/>
            
            <small v-if="authError" class="p-error text-center" style="color: red;">{{ authError }}</small>
            
            <Button v-if="!isRegistering" :label="t('home.loginCard.login')" :loading="authLoading" @click="loginWithEmail" class="w-full" />
            <Button v-if="isRegistering" :label="t('home.loginCard.register')" :loading="authLoading" @click="registerWithEmail" class="w-full" />
            
            <Button :label="isRegistering ? t('home.loginCard.hasAccount') : t('home.loginCard.newUser')" link class="w-full p-0 text-sm" @click="isRegistering = !isRegistering" />
          </form>
        </div>
      </div>

      <!-- Sezione Come Funziona -->
      <div class="mb-6">
        <h2 class="text-2xl md:text-3xl font-bold text-center mb-5">{{ t('home.howItWorks.title') }}</h2>
        
        <div class="grid justify-content-center">
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">01</span>
              <h3 class="font-semibold text-base mb-2">{{ t('home.howItWorks.step1Title') }}</h3>
              <p class="text-sm text-color-secondary m-0">{{ t('home.howItWorks.step1Desc') }}</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">02</span>
              <h3 class="font-semibold text-base mb-2">{{ t('home.howItWorks.step2Title') }}</h3>
              <p class="text-sm text-color-secondary m-0">{{ t('home.howItWorks.step2Desc') }}</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">03</span>
              <h3 class="font-semibold text-base mb-2">{{ t('home.howItWorks.step3Title') }}</h3>
              <p class="text-sm text-color-secondary m-0">{{ t('home.howItWorks.step3Desc') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Sezione Vantaggi -->
      <div>
        <h2 class="text-2xl md:text-3xl font-bold text-center mb-5">{{ t('home.benefits.title') }}</h2>
        <div class="grid justify-content-center">
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-compass text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">{{ t('home.benefits.resourceTitle') }}</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">{{ t('home.benefits.resourceDesc') }}</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-users text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">{{ t('home.benefits.communityTitle') }}</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">{{ t('home.benefits.communityDesc') }}</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-heart text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">{{ t('home.benefits.supportTitle') }}</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">{{ t('home.benefits.supportDesc') }}</p>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- 🟡 CASO 2: INCOMPLETE -->
    <div v-else-if="backendUser?.status === 'INCOMPLETE'" class="flex justify-content-center py-5">
      <div class="card p-5 text-center shadow-3 border-round-xl border-top-3 border-warning max-w-30rem surface-card">
        <i class="pi pi-user-plus text-5xl text-warning mb-3 block"></i>
        <h2 class="text-2xl font-bold mb-2">{{ t('home.statusIncomplete.title') }}</h2>
        <p class="text-color-secondary mb-4 line-height-3">{{ t('home.statusIncomplete.desc') }}</p>
        <router-link to="/wizard">
          <Button :label="t('home.statusIncomplete.btnStart')" icon="pi pi-arrow-right" iconPos="right" size="large" class="w-full" />
        </router-link>
      </div>
    </div>

    <!-- 🔵 CASO 3: PENDING -->
    <div v-else-if="backendUser?.status === 'PENDING'" class="flex justify-content-center py-5">
      <div class="card p-5 text-center shadow-3 border-round-xl border-top-3 border-info max-w-30rem surface-card">
        <i class="pi pi-hourglass text-5xl text-info mb-3 block"></i>
        <h2 class="text-2xl font-bold mb-2">{{ t('home.statusPending.title') }}</h2>
        <p class="text-color-secondary mb-3">{{ t('home.statusPending.welcome', { name: backendUser.first_name }) }}</p>
        <p class="text-color-secondary mb-4 text-sm line-height-3">{{ t('home.statusPending.desc') }}</p>
        
        <div class="surface-ground p-3 border-round text-left mb-4 border-1 border-light">
          <div class="flex justify-content-between py-2 border-bottom-1 border-light">
            <span class="text-xs text-color-secondary font-medium uppercase">{{ t('home.statusPending.method') }}</span>
            <span class="font-semibold text-xs">{{ backendUser.payment_method }}</span>
          </div>
          <div class="flex justify-content-between py-2">
            <span class="text-xs text-color-secondary font-medium uppercase">{{ t('home.statusPending.status') }}</span>
            <span class="font-semibold text-xs text-info uppercase">{{ t('home.statusPending.verifying') }}</span>
          </div>
        </div>

        <router-link to="/wizard">
          <Button :label="t('home.statusPending.btnEdit')" icon="pi pi-pencil" severity="secondary" outlined class="w-full" />
        </router-link>
      </div>
    </div>

    <!-- 🔴 CASO 3.5: REJECTED -->
    <div v-else-if="backendUser?.status === 'REJECTED'" class="flex justify-content-center py-5">
      <div class="card p-5 text-center shadow-3 border-round-xl border-top-3 border-danger max-w-30rem surface-card">
        <i class="pi pi-times-circle text-5xl text-danger mb-3 block"></i>
        <h2 class="text-2xl font-bold mb-2">{{ t('home.statusRejected.title') }}</h2>
        <p class="text-color-secondary mb-4 line-height-3">{{ t('home.statusRejected.desc') }}</p>
        <p class="text-color-secondary text-sm font-medium">{{ t('home.statusRejected.info') }}</p>
      </div>
    </div>

    <!-- 🏆 CASO 4: APPROVATO -->
    <div v-else-if="backendUser?.status === 'APPROVED'" class="flex flex-column align-items-center py-4">
      
      <div class="max-w-28rem w-full">
        <!-- Tessera Socio Digitale -->
        <div class="p-4 text-white border-round-2xl shadow-4 relative overflow-hidden mb-4"
          :class="[ memberNoActive() ? 'membership-card_inactive' : (memberExpiring() ? 'membership-card_expiring' : 'membership-card') ]"
        >
          <div class="card-glow"></div>
          
          <div class="flex justify-content-between align-items-center mb-5">
            <div class="flex align-items-center gap-2">
              <i :class="['pi', getRoleIcon(), 'text-2xl']"></i>
              <span class="font-bold tracking-wider text-xs uppercase">{{ t('home.membershipCard.title') }}</span>
            </div>
            <span v-if="memberNoActive()" class="bg-blue-500 text-white text-xxs px-2.5 py-1 font-bold border-round-lg uppercase shadow-1">{{ t('home.membershipCard.inactive') }}</span>
            <span v-else-if="memberExpiring()" class="bg-blue-500 text-white text-xxs px-2.5 py-1 font-bold border-round-lg uppercase shadow-1">{{ t('home.membershipCard.expiring') }}</span>
            <span v-else class="bg-blue-500 text-white text-xxs px-2.5 py-1 font-bold border-round-lg uppercase shadow-1">{{ t('home.membershipCard.active') }}</span>
          </div>

          <div class="mb-5">
            <h3 class="text-2xl font-bold m-0 letter-spacing-1" style="color: black !important;">{{ backendUser.first_name }} {{ backendUser.last_name }}</h3>
            <p class="text-xxs text-white-alpha-70 m-0 mt-1 uppercase font-semibold">{{ t('home.membershipCard.member') }} {{ backendUser.member_type || t('home.membershipCard.ordinary') }}</p>
          </div>

          <div class="flex justify-content-between border-top-1 border-white-alpha-20 pt-3">
            <div class="flex flex-column text-left">
              <span class="text-xxs text-white-alpha-50 uppercase">{{ t('home.membershipCard.cardNumber') }}</span>
              <span class="text-lg font-bold text-white">{{ backendUser.membership_number }}</span>
            </div>
            <div class="flex flex-column text-right">
              <span class="text-xxs text-white-alpha-50 uppercase">{{ t('home.membershipCard.validUntil') }}</span>
              <span class="text-lg font-bold text-white">{{ formatDate(backendUser.end_date) }}</span>
            </div>
          </div>
        </div>

        <!-- PENDING RENEWAL STATE -->
        <div class="mb-5">
          <div v-if="backendUser.is_renewal_pending" class="card p-4 shadow-2 border-round-xl surface-card text-center mt-4 border-top-3 border-info">
            <i class="pi pi-hourglass text-4xl text-info mb-3 block"></i>
            <h4 class="font-bold text-lg mb-2">{{ t('home.renewal.pendingTitle', { year: getRenewalYear() }) }}</h4>
            <p class="text-sm text-color-secondary m-0">{{ t('home.renewal.pendingDesc') }}</p>
          </div>

          <!-- RENEW REQUEST FORM -->
          <div v-else-if="!backendUser.end_date || new Date(backendUser.end_date) < new Date() || memberExpiring()" class="card p-4 shadow-2 border-round-xl surface-card text-left mt-4 border-top-3 border-orange-500">
            <h4 class="font-bold text-base mb-3 text-color uppercase tracking-wide">
              {{ memberExpiring() ? t('home.renewal.earlyRenewalTitle') : t('home.renewal.renewalTitle') }}
            </h4>
            <p class="text-sm text-color-secondary mb-3">{{ t('home.renewal.renewalDesc') }}</p>
            <div class="flex flex-column gap-3">
              <div class="flex flex-column gap-2">
                <label for="memberType" class="font-semibold text-sm">{{ t('home.renewal.memberType') }} *</label>
                <Select inputId="memberType" v-model="selectedMemberType" :options="memberTypes" optionLabel="label" optionValue="value" :placeholder="t('home.renewal.selectMemberType')" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="paymentMethod" class="font-semibold text-sm">{{ t('home.renewal.paymentMethod') }} *</label>
                <Select inputId="paymentMethod" v-model="selectedPaymentMethod" :options="paymentMethods" optionLabel="label" optionValue="value" :placeholder="t('home.renewal.selectPaymentMethod')" class="w-full" />
              </div>
              <Button :label="t('home.renewal.requestRenewal')" icon="pi pi-refresh" :loading="renewing" @click="requestRenewal" severity="warning" class="w-full mt-2" :disabled="!selectedPaymentMethod || !selectedMemberType" />
            </div>
          </div>
        </div>

        <!-- Box Dettagli Iscrizione -->
        <div class="card p-4 shadow-2 border-round-xl surface-card text-left">
          <h4 class="font-bold text-base mb-3 text-color uppercase tracking-wide">{{ t('home.membershipDetails.title') }}</h4>
          
          <div class="flex flex-column gap-3">
            <div class="flex align-items-center gap-3">
              <i class="pi pi-calendar text-primary text-lg"></i>
              <div>
                <p class="text-xxs text-color-secondary m-0 uppercase font-semibold">{{ t('home.membershipDetails.issueDate') }}</p>
                <p class="text-sm font-semibold m-0 text-color">{{ formatDate(backendUser.start_date) }}</p>
              </div>
            </div>
            <div class="flex align-items-center gap-3">
              <i class="pi pi-wallet text-primary text-lg"></i>
              <div>
                <p class="text-xxs text-color-secondary m-0 uppercase font-semibold">{{ t('home.membershipDetails.paymentMethod') }}</p>
                <p class="text-sm font-semibold m-0 text-color">{{ backendUser.payment_method }}</p>
              </div>
            </div>
          </div>

          <div class="mt-4 pt-3 border-top-1 border-light flex justify-content-between align-items-center">
            <span class="text-xs text-color-secondary">{{ t('home.membershipDetails.updatePrompt') }}</span>
            <router-link to="/wizard">
              <Button :label="t('home.membershipDetails.editData')" icon="pi pi-pencil" size="small" severity="secondary" outlined />
            </router-link>
          </div>
        </div>

      </div>

    </div>

  </div>
</template>

<style scoped>
.home-container {
  max-width: 1020px;
  margin: 0 auto;
}

.hero-section {
  background: linear-gradient(135deg, rgba(59, 154, 255, 0.04) 0%, rgba(79, 195, 247, 0.04) 100%);
  border: 1px solid var(--border);
}

.text-primary-gradient {
  background: #ef7b14;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.benefit-card, .step-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border-color: var(--border) !important;
}

.benefit-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow);
}

.membership-card {
  background: linear-gradient(0deg, #ec8e5b 20%,  #ea580c 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.membership-card_pending {
  background: linear-gradient(90deg, #ea580c 20%,  #5c5a59 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.membership-card_inactive {
  background: linear-gradient(0deg, #adaba9 20%,  #5c5a59 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.membership-card_expiring {
  background: linear-gradient(0deg, #adaba9 20%,  #ea580c 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-glow {
  position: absolute;
  top: -50%;
  left: -30%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 70%);
  transform: rotate(-30deg);
  pointer-events: none;
}

.text-xxs {
  font-size: 0.65rem;
  letter-spacing: 1.2px;
}

.border-light {
  border-color: var(--border) !important;
}

.surface-ground {
  background-color: var(--code-bg);
}

.text-muted {
  color: var(--text);
}
</style>