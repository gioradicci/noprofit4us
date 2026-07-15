<script setup>
import { API_URL } from '../config.js'
import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
// Import PrimeVue Stepper and custom components
import Stepper from 'primevue/stepper'
import StepList from 'primevue/steplist'
import Step from 'primevue/step'
import StepPanels from 'primevue/steppanels'
import StepPanel from 'primevue/steppanel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'

const { t } = useI18n()
const toast = useToast()

// Utente backend
const backendUser = ref(null)

// Errori di validazione
const validationErrors = ref({})
const initialDate = new Date(new Date().getFullYear() - 18, 0, 1)

const isSocioAttivo = computed(() => {
  if (!backendUser.value) return false
  return backendUser.value.status === 'APPROVED' && backendUser.value.end_date && new Date(backendUser.value.end_date) >= new Date()
})

// Form di profilo
const profile = ref({
  first_name: "",
  last_name: "",
  tax_code: "",
  birth_date: null,
  birth_place: "",
  phone: "",
  address: "",
  city: "",
  zip_code: "",
  province: "",
  municipality: "",
  document_type: "",
  document_number: "",
  document_expiry: null,
  profession: "",
  usage_type: [],
  avg_km_per_day: null,
  member_type: "",
  payment_method: "",
  municipio_roma: ""
})

const usageTypes = ref([
  { label: t('wizard.usageTypes.homeWork'), value: "casa-lavoro" },
  { label: t('wizard.usageTypes.travel'), value: "viaggio" },
  { label: t('wizard.usageTypes.sport'), value: "sport" },
  { label: t('wizard.usageTypes.children'), value: "accompagnare figli" },
  { label: t('wizard.usageTypes.shopping'), value: "spesa" },
  { label: t('wizard.usageTypes.workTool'), value: "strumento lavoro" }
])

const documentTypes = ref([
  { label: t('wizard.documentTypes.idCard'), value: "Carta d'Identità" },
  { label: t('wizard.documentTypes.drivingLicense'), value: "Patente di Guida" },
  { label: t('wizard.documentTypes.passport'), value: "Passaporto" }
])

const paymentMethods = ref([
  { label: t('wizard.paymentMethods.bankTransfer'), value: "Bonifico Bancario" },
  { label: t('wizard.paymentMethods.paypal'), value: "PayPal" },
  { label: t('wizard.paymentMethods.satispay'), value: "Satispay" },
  { label: t('wizard.paymentMethods.cash'), value: "Contanti" },
  { label: t('wizard.paymentMethods.pos'), value: "POS" }
])

const memberTypes = ref([
  { label: `${t('wizard.memberTypes.ordinary')} (10€)`, value: "ORDINARIO" },
  { label: `${t('wizard.memberTypes.supporter')} (30€)`, value: "SOSTENITORE" }
])

const municipiRoma = ref([
  { label: "I", value: "I" }, { label: "II", value: "II" },
  { label: "III", value: "III" }, { label: "IV", value: "IV" },
  { label: "V", value: "V" }, { label: "VI", value: "VI" },
  { label: "VII", value: "VII" }, { label: "VIII", value: "VIII" },
  { label: "IX", value: "IX" }, { label: "X", value: "X" },
  { label: "XI", value: "XI" }, { label: "XII", value: "XII" },
  { label: "XIII", value: "XIII" }, { label: "XIV", value: "XIV" },
  { label: "XV", value: "XV" }
])

async function loadUser() {
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/users/me", {
      headers: { Authorization: `Bearer ${token}` }
    })
    backendUser.value = await res.json()
    profile.value = {
      first_name: backendUser.value.first_name || "",
      last_name: backendUser.value.last_name || "",
      tax_code: backendUser.value.tax_code || "",
      birth_date: backendUser.value.birth_date ? new Date(backendUser.value.birth_date) : null,
      birth_place: backendUser.value.birth_place || "",
      phone: backendUser.value.phone || "",
      address: backendUser.value.address || "",
      city: backendUser.value.city || "",
      zip_code: backendUser.value.zip_code || "",
      province: backendUser.value.province || "",
      municipality: backendUser.value.municipality || "",
      document_type: backendUser.value.document_type || "",
      document_number: backendUser.value.document_number || "",
      document_expiry: backendUser.value.document_expiry ? new Date(backendUser.value.document_expiry) : null,
      profession: backendUser.value.profession || "",
      usage_type: backendUser.value.usage_type || [],
      avg_km_per_day: backendUser.value.avg_km_per_day || null,
      member_type: backendUser.value.member_type || "",
      payment_method: backendUser.value.payment_method || "",
      municipio_roma: backendUser.value.municipio_roma || ""
    }
  } catch (e) {
    console.error("Errore loadUser:", e)
  }
}

async function submit() {
  validationErrors.value = {}
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const payload = { ...profile.value }
    if (payload.birth_date) {
      payload.birth_date = payload.birth_date.toISOString().substring(0, 10)
    }
    if (payload.document_expiry) {
      payload.document_expiry = payload.document_expiry.toISOString().substring(0, 10)
    }
    const res = await fetch(API_URL + "/users/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload)
    })
    if (!res.ok) {
      let errorMsg = `${t('wizard.errors.saveError')}: ${res.status}`
      if (res.status === 422) {
        try {
          const errData = await res.json()
          if (errData && errData.detail && Array.isArray(errData.detail)) {
            const errors = {}
            errData.detail.forEach(err => {
              const field = err.loc[err.loc.length - 1]
              errors[field] = err.msg
            })
            validationErrors.value = errors
            errorMsg = Object.values(errors).join(", ")
          }
        } catch (jsonErr) {}
      } else {
        try {
          const errData = await res.json()
          if (errData && errData.detail) {
            errorMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail)
          }
        } catch (jsonErr) {}
      }
      throw new Error(errorMsg)
    }
    const data = await res.json()
    backendUser.value = data
    toast.add({ severity: 'success', summary: t('wizard.success'), detail: t('wizard.dataSaved'), life: 3000 })
  } catch (e) {
    console.error("Errore submit:", e)
    toast.add({ severity: 'error', summary: t('wizard.error'), detail: e.message || t('wizard.errors.generic'), life: 5000 })
  }
}

onMounted(() => {
  loadUser()
})
</script>

<template>
<div class="wizard-container py-5 px-3">
  <!-- Messaggio stato iscrizione -->
  <div v-if="backendUser?.status === 'PENDING'" class="status-box mb-4 p-3 border-round flex align-items-center gap-2">
    <i class="pi pi-check-circle text-xl text-success"></i>
    <div>
      <strong class="block">{{ t('wizard.status.registrationComplete') }}</strong>
      <span class="text-sm">{{ t('wizard.status.pendingApproval') }}</span>
    </div>
  </div>

  <!-- Titolo della sezione -->
  <div class="text-center mb-5">
    <h2 class="font-bold text-3xl mb-2">
      {{ backendUser?.status === 'INCOMPLETE' ? t('wizard.title.newMember') : t('wizard.title.memberProfile') }}
    </h2>
    <p class="text-muted text-sm">{{ t('wizard.subtitle') }}</p>
  </div>

  <!-- Contenitore Stepper -->
  <div class="card p-4 shadow-2 border-round surface-card">
    <Stepper value="1">
      <StepList class="mb-4">
        <Step value="1">{{ t('wizard.steps.anagraphics') }}</Step>
        <Step value="2">{{ t('wizard.steps.contacts') }}</Step>
        <Step value="3">{{ t('wizard.steps.document') }}</Step>
        <Step value="4">{{ t('wizard.steps.profile') }}</Step>
        <Step value="5">{{ t('wizard.steps.payment') }}</Step>
        <Step value="6">{{ t('wizard.steps.complete') }}</Step>
      </StepList>

      <StepPanels>
        <!-- STEP 1: Dati Anagrafici -->
        <StepPanel v-slot="{ activateCallback }" value="1">
          <div class="flex flex-column gap-4 py-3 text-left">
            <div class="flex flex-column gap-2">
              <label for="first_name" class="font-semibold text-sm">{{ t('wizard.form.firstName') }} *</label>
              <InputText id="first_name" v-model="profile.first_name" :placeholder="t('wizard.placeholders.firstName')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="last_name" class="font-semibold text-sm">{{ t('wizard.form.lastName') }} *</label>
              <InputText id="last_name" v-model="profile.last_name" :placeholder="t('wizard.placeholders.lastName')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="tax_code" class="font-semibold text-sm">{{ t('wizard.form.taxCode') }} *</label>
              <InputText id="tax_code" v-model="profile.tax_code" :placeholder="t('wizard.placeholders.taxCode')" class="w-full uppercase" :invalid="!!validationErrors.tax_code" />
              <small v-if="validationErrors.tax_code" class="text-red-500 block mt-1">{{ validationErrors.tax_code }}</small>
            </div>
            <div class="flex flex-column gap-2">
              <label for="birth_date" class="font-semibold text-sm">{{ t('wizard.form.birthDate') }} *</label>
              <DatePicker inputId="birth_date" v-model="profile.birth_date" dateFormat="dd/mm/yy" class="w-full"
                :pt="{ root: ({ state, props }) => { if (!props.modelValue && state.currentYear === new Date().getFullYear()) { state.currentYear = initialDate.getFullYear(); state.currentMonth = initialDate.getMonth() } } }" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="birth_place" class="font-semibold text-sm">{{ t('wizard.form.birthPlace') }} *</label>
              <InputText id="birth_place" v-model="profile.birth_place" :placeholder="t('wizard.placeholders.birthPlace')" class="w-full" />
            </div>
          </div>
          <div class="flex pt-4 justify-content-end border-top-1 border-light">
            <Button :label="t('wizard.buttons.next')" icon="pi pi-arrow-right" iconPos="right"
              :disabled="!profile.first_name || !profile.last_name || !profile.tax_code || !profile.birth_date || !profile.birth_place"
              @click="activateCallback('2')" />
          </div>
        </StepPanel>

        <!-- STEP 2: Contatti -->
        <StepPanel v-slot="{ activateCallback }" value="2">
          <div class="flex flex-column gap-4 py-3 text-left">
            <div class="flex flex-column gap-2">
              <label for="phone" class="font-semibold text-sm">{{ t('wizard.form.phone') }} *</label>
              <InputText id="phone" v-model="profile.phone" :placeholder="t('wizard.placeholders.phone')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="address" class="font-semibold text-sm">{{ t('wizard.form.address') }} *</label>
              <InputText id="address" v-model="profile.address" :placeholder="t('wizard.placeholders.address')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="city" class="font-semibold text-sm">{{ t('wizard.form.city') }} *</label>
              <InputText id="city" v-model="profile.city" :placeholder="t('wizard.placeholders.city')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="zip_code" class="font-semibold text-sm">{{ t('wizard.form.zipCode') }} *</label>
              <InputText id="zip_code" v-model="profile.zip_code" :placeholder="t('wizard.placeholders.zipCode')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="province" class="font-semibold text-sm">{{ t('wizard.form.province') }} *</label>
              <InputText id="province" v-model="profile.province" :placeholder="t('wizard.placeholders.province')" class="w-full uppercase" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="municipality" class="font-semibold text-sm">{{ t('wizard.form.municipality') }} *</label>
              <InputText id="municipality" v-model="profile.municipality" :placeholder="t('wizard.placeholders.municipality')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label id="municipio_roma_label" class="font-semibold text-sm">{{ t('wizard.form.municipio') }} *</label>
              <Select aria-labelledby="municipio_roma_label" v-model="profile.municipio_roma" :options="municipiRoma"
                optionLabel="label" optionValue="value" :placeholder="t('wizard.placeholders.selectMunicipio')" class="w-full" />
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('wizard.buttons.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('1')" />
            <Button :label="t('wizard.buttons.next')" icon="pi pi-arrow-right" iconPos="right"
              :disabled="!profile.phone || !profile.address || !profile.city || !profile.zip_code || !profile.province || !profile.municipality || !profile.municipio_roma"
              @click="activateCallback('3')" />
          </div>
        </StepPanel>

        <!-- STEP 3: Documento -->
        <StepPanel v-slot="{ activateCallback }" value="3">
          <div class="flex flex-column gap-4 py-3 text-left">
            <div class="flex flex-column gap-2">
              <label id="document_type_label" class="font-semibold text-sm">{{ t('wizard.form.documentType') }} *</label>
              <Select aria-labelledby="document_type_label" v-model="profile.document_type" :options="documentTypes"
                optionLabel="label" optionValue="value" :placeholder="t('wizard.placeholders.selectDocument')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="document_number" class="font-semibold text-sm">{{ t('wizard.form.documentNumber') }} *</label>
              <InputText id="document_number" v-model="profile.document_number" :placeholder="t('wizard.placeholders.documentNumber')" class="w-full uppercase" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="document_expiry" class="font-semibold text-sm">{{ t('wizard.form.documentExpiry') }} *</label>
              <DatePicker inputId="document_expiry" v-model="profile.document_expiry" dateFormat="dd/mm/yy" class="w-full" />
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('wizard.buttons.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('2')" />
            <Button :label="t('wizard.buttons.next')" icon="pi pi-arrow-right" iconPos="right"
              :disabled="!profile.document_type || !profile.document_number || !profile.document_expiry"
              @click="activateCallback('4')" />
          </div>
        </StepPanel>

        <!-- STEP 4: Profilo Associativo -->
        <StepPanel v-slot="{ activateCallback }" value="4">
          <div class="flex flex-column gap-4 py-3 text-left">
            <div class="flex flex-column gap-2">
              <label for="profession" class="font-semibold text-sm">{{ t('wizard.form.profession') }}</label>
              <InputText id="profession" v-model="profile.profession" :placeholder="t('wizard.placeholders.profession')" class="w-full" />
            </div>
            <div class="flex flex-column gap-2">
              <label id="usage_type_label" class="font-semibold text-sm">{{ t('wizard.form.usageType') }}</label>
              <MultiSelect aria-labelledby="usage_type_label" v-model="profile.usage_type"
                :pt="{ hiddenInput: { name: 'usage_type' } }" :options="usageTypes"
                optionLabel="label" optionValue="value" :placeholder="t('wizard.placeholders.selectUsage')"
                class="w-full" display="chip" />
            </div>
            <div class="flex flex-column gap-2">
              <label for="avg_km_per_day" class="font-semibold text-sm">{{ t('wizard.form.avgKmPerDay') }}</label>
              <InputNumber inputId="avg_km_per_day" v-model="profile.avg_km_per_day" :placeholder="t('wizard.placeholders.avgKmPerDay')" class="w-full" />
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('wizard.buttons.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('3')" />
            <Button :label="t('wizard.buttons.next')" icon="pi pi-arrow-right" iconPos="right" @click="activateCallback('5')" />
          </div>
        </StepPanel>

        <!-- STEP 5: Pagamento -->
        <StepPanel v-slot="{ activateCallback }" value="5">
          <div class="flex flex-column gap-4 py-3 text-left">
            <div class="flex flex-column gap-2">
              <label id="member_type_label" class="font-semibold text-sm">{{ t('wizard.form.memberType') }} *</label>
              <Select aria-labelledby="member_type_label" v-model="profile.member_type" :options="memberTypes"
                optionLabel="label" optionValue="value" :placeholder="t('wizard.placeholders.selectMemberType')"
                class="w-full" :disabled="isSocioAttivo" />
            </div>
            <div class="flex flex-column gap-2 mt-3">
              <span class="text-sm">{{ t('wizard.paymentInfo') }} <a href="https://APS/" target="_blank">{{ t('wizard.paymentLink') }}</a></span>
              <label id="payment_method_label" class="font-semibold text-sm mt-2">{{ t('wizard.form.paymentMethod') }} *</label>
              <Select aria-labelledby="payment_method_label" v-model="profile.payment_method" :options="paymentMethods"
                optionLabel="label" optionValue="value" :placeholder="t('wizard.placeholders.selectPayment')"
                class="w-full" :disabled="isSocioAttivo" />
            </div>
            <div v-if="isSocioAttivo" class="p-3 bg-blue-50 text-blue-800 border-round flex align-items-center gap-2 border-1 border-blue-200 mt-2">
              <i class="pi pi-info-circle text-lg"></i>
              <span class="text-sm">{{ t('wizard.activeMemberInfo') }}</span>
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('wizard.buttons.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('4')" />
            <Button :label="t('wizard.buttons.next')" icon="pi pi-arrow-right" iconPos="right"
              :disabled="!profile.payment_method || !profile.member_type"
              @click="activateCallback('6')" />
          </div>
        </StepPanel>

        <!-- STEP 6: Riepilogo e Completamento -->
        <StepPanel v-slot="{ activateCallback }" value="6">
          <div class="py-3 text-left">
            <h3 class="font-semibold text-lg mb-3">{{ t('wizard.summary.title') }}</h3>
            <div class="surface-ground p-4 border-round grid row-gap-3 column-gap-4">
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.summary.nameSurname') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.first_name || validationErrors.last_name}">{{ profile.first_name }} {{ profile.last_name }}</span>
                <small v-if="validationErrors.first_name" class="text-red-500 font-bold mt-1">{{ validationErrors.first_name }}</small>
                <small v-if="validationErrors.last_name" class="text-red-500 font-bold mt-1">{{ validationErrors.last_name }}</small>
              </div>
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.form.taxCode') }}</span>
                <span class="text-base text-900 font-medium uppercase" :class="{'text-red-500 font-bold': validationErrors.tax_code}">{{ profile.tax_code }}</span>
                <small v-if="validationErrors.tax_code" class="text-red-500 font-bold mt-1">{{ validationErrors.tax_code }}</small>
              </div>
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.summary.birthInfo') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.birth_date || validationErrors.birth_place}">{{ profile.birth_date ? profile.birth_date.toLocaleDateString() : '' }} - {{ profile.birth_place }}</span>
                <small v-if="validationErrors.birth_date" class="text-red-500 font-bold mt-1">{{ validationErrors.birth_date }}</small>
                <small v-if="validationErrors.birth_place" class="text-red-500 font-bold mt-1">{{ validationErrors.birth_place }}</small>
              </div>
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.form.phone') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.phone}">{{ profile.phone || '-' }}</span>
                <small v-if="validationErrors.phone" class="text-red-500 font-bold mt-1">{{ validationErrors.phone }}</small>
              </div>
              <div class="col-12 md:col-10 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.summary.residence') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.address || validationErrors.city || validationErrors.province || validationErrors.zip_code || validationErrors.municipio_roma}">{{ profile.address || '-' }}, {{ profile.city || '-' }} ({{ profile.province || '-' }}) - {{ profile.zip_code || '-' }}<template v-if="profile.municipio_roma"> - {{ t('wizard.summary.municipio') }} {{ profile.municipio_roma }}</template></span>
                <small v-if="validationErrors.address" class="text-red-500 font-bold mt-1">{{ validationErrors.address }}</small>
                <small v-if="validationErrors.city" class="text-red-500 font-bold mt-1">{{ validationErrors.city }}</small>
                <small v-if="validationErrors.province" class="text-red-500 font-bold mt-1">{{ validationErrors.province }}</small>
                <small v-if="validationErrors.zip_code" class="text-red-500 font-bold mt-1">{{ validationErrors.zip_code }}</small>
                <small v-if="validationErrors.municipio_roma" class="text-red-500 font-bold mt-1">{{ validationErrors.municipio_roma }}</small>
              </div>
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.form.documentType') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.document_type || validationErrors.document_number || validationErrors.document_expiry}">{{ profile.document_type }} - {{ profile.document_number }} ({{ t('wizard.summary.expiry') }}: {{ profile.document_expiry ? profile.document_expiry.toLocaleDateString() : '' }})</span>
                <small v-if="validationErrors.document_type" class="text-red-500 font-bold mt-1">{{ validationErrors.document_type }}</small>
                <small v-if="validationErrors.document_number" class="text-red-500 font-bold mt-1">{{ validationErrors.document_number }}</small>
                <small v-if="validationErrors.document_expiry" class="text-red-500 font-bold mt-1">{{ validationErrors.document_expiry }}</small>
              </div>
              <div class="col-12 md:col-5 flex flex-column gap-1">
                <span class="text-xs font-semibold text-muted text-uppercase uppercase">{{ t('wizard.summary.payment') }}</span>
                <span class="text-base text-900 font-medium" :class="{'text-red-500 font-bold': validationErrors.member_type || validationErrors.payment_method}">{{ profile.member_type }} - {{ profile.payment_method }}</span>
                <small v-if="validationErrors.member_type" class="text-red-500 font-bold mt-1">{{ validationErrors.member_type }}</small>
                <small v-if="validationErrors.payment_method" class="text-red-500 font-bold mt-1">{{ validationErrors.payment_method }}</small>
              </div>
            </div>

            <div v-if="backendUser?.status === 'INCOMPLETE'" class="mt-4 p-3 bg-blue-50 text-blue-800 border-round flex align-items-center gap-2 border-1 border-blue-200">
              <i class="pi pi-info-circle text-lg"></i>
              <span class="text-sm">{{ t('wizard.summary.infoMessage') }}</span>
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('wizard.buttons.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('5')" />
            <Button v-if="backendUser?.status === 'INCOMPLETE'" :label="t('wizard.buttons.completeRegistration')" severity="success" icon="pi pi-check" @click="submit" />
            <Button v-else :label="t('wizard.buttons.updateProfile')" severity="success" icon="pi pi-save" @click="submit" />
          </div>
        </StepPanel>
      </StepPanels>
    </Stepper>
  </div>
</div>
</template>

<style scoped>
.wizard-container {
max-width: 1000px;
margin: 0 auto;
}
.status-box {
background-color: var(--accent-bg);
border: 1px solid var(--accent-border);
color: var(--text-h);
}
.surface-ground {
background-color: var(--code-bg);
}
.text-muted {
color: var(--text);
}
.border-light {
border-color: var(--border);
}
</style>