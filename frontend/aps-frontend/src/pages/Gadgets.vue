<script setup>
import { API_URL, getImageUrl } from '../config.js'
import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import ImageUpload from '../components/ImageUpload.vue'

import Stepper from 'primevue/stepper'
import StepList from 'primevue/steplist'
import Step from 'primevue/step'
import StepPanels from 'primevue/steppanels'
import StepPanel from 'primevue/steppanel'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()

const gadgets = ref([])
const loading = ref(false)
const showCreateWizard = ref(false)
const activeStep = ref("1")
const isEditMode = ref(false)
let heartbeatInterval = null

const newGadget = ref({
  name: '',
  description: '',
  category: 'T-SHIRT',
  min_donation: 10.0,
  image_path: ''
})

const categories = [
  { label: 'T-Shirt', value: 'T-SHIRT' },
  { label: t('gadgets.categories.cap'), value: 'CAP' },
  { label: t('gadgets.categories.keychain'), value: 'KEYCHAIN' },
  { label: t('gadgets.categories.pin'), value: 'PIN' },
  { label: t('gadgets.categories.sticker'), value: 'STICKER' },
  { label: t('gadgets.categories.bottleOpener'), value: 'APRIBOTTIGLIE' },
  { label: t('gadgets.categories.neckWarmer'), value: 'SCALDACOLLO' },
  { label: t('gadgets.categories.poster'), value: 'POSTER' },
  { label: t('gadgets.categories.shopper'), value: 'SHOPPER' },
  { label: t('gadgets.categories.bags'), value: 'BORSE' },
  { label: t('gadgets.categories.other'), value: 'OTHER' }
]

const modelOptions = [
  { label: t('gadgets.models.none'), value: '' },
  { label: t('gadgets.models.man'), value: 'Uomo' },
  { label: t('gadgets.models.woman'), value: 'Donna' },
  { label: t('gadgets.models.unisex'), value: 'Unisex' }
]

const newVariant = ref({
  size: '',
  color: '',
  model: '',
  variant_type: '',
  sku: '',
  price_modifier: 0.0,
  image_path: ''
})

const tempVariants = ref([])

async function loadGadgets() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/gadgets/", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      gadgets.value = data.map(g => ({
        ...g,
        total_stock: g.variants ? g.variants.reduce((acc, v) => acc + (v.stock_quantity || 0), 0) : 0
      }))
    } else {
      toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgets.errors.loadFailed'), life: 3000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgets.errors.connectionFailed'), life: 3000 })
  } finally {
    loading.value = false
  }
}

async function acquireLock(id) {
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(`${API_URL}/gadgets/${id}/lock`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` }
    })
    if (!res.ok) {
      if (res.status === 423) {
        const errorData = await res.json()
        toast.add({ severity: 'error', summary: t('gadgets.lock.denied'), detail: errorData.detail || t('gadgets.lock.inUse'), life: 5000 })
      } else {
        toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgets.lock.failed'), life: 3000 })
      }
      return false
    }
    return true
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgets.errors.connectionFailed'), life: 3000 })
    return false
  }
}

async function releaseLock(id) {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval)
    heartbeatInterval = null
  }
  if (!id) return
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    await fetch(`${API_URL}/gadgets/${id}/lock`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
  } catch (err) {
    console.error('Error releasing lock', err)
  }
}

function startHeartbeat(id) {
  if (heartbeatInterval) clearInterval(heartbeatInterval)
  heartbeatInterval = setInterval(() => {
    acquireLock(id)
  }, 90000)
}

function cancelEdit() {
  showCreateWizard.value = false
  if (isEditMode.value && newGadget.value.id) {
    releaseLock(newGadget.value.id)
  }
}

function startCreate() {
  isEditMode.value = false
  newGadget.value = {
    name: '',
    description: '',
    category: 'T-SHIRT',
    min_donation: 10.0,
    image_path: ''
  }
  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0,
    image_path: ''
  }
  tempVariants.value = []
  activeStep.value = "1"
  showCreateWizard.value = true
}

async function startEdit(gadget) {
  const locked = await acquireLock(gadget.id)
  if (!locked) return
  startHeartbeat(gadget.id)
  isEditMode.value = true
  newGadget.value = {
    id: gadget.id,
    name: gadget.name,
    description: gadget.description || '',
    category: gadget.category,
    min_donation: gadget.min_donation,
    image_path: gadget.image_path || ''
  }
  tempVariants.value = gadget.variants.map(v => ({
    id: v.id,
    size: v.size || '',
    color: v.color || '',
    model: v.model || '',
    variant_type: v.variant_type || '',
    sku: v.sku || '',
    price_modifier: v.price_modifier || 0.0,
    stock_quantity: v.stock_quantity || 0,
    image_path: v.image_path || ''
  }))
  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0,
    image_path: ''
  }
  activeStep.value = "1"
  showCreateWizard.value = true
}

function addTempVariant() {
  if (!newVariant.value.sku) {
    const cat = newGadget.value.category.substring(0, 3)
    const rand = Math.floor(1000 + Math.random() * 9000)
    newVariant.value.sku = `${cat}-${newVariant.value.size || 'UNI'}-${newVariant.value.color || 'GEN'}-${rand}`.toUpperCase()
  }
  tempVariants.value.push({ ...newVariant.value })
  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0,
    image_path: ''
  }
  toast.add({ severity: 'success', summary: t('gadgets.variantAdded'), detail: t('gadgets.variantAddedDesc'), life: 2000 })
}

function removeTempVariant(index) {
  const variant = tempVariants.value[index]
  if (isEditMode.value && variant.id && variant.stock_quantity > 0) {
    toast.add({
      severity: 'error',
      summary: t('common.error'),
      detail: t('gadgets.errors.cannotDeleteVariant', { sku: variant.sku, stock: variant.stock_quantity }),
      life: 5000
    })
    return
  }
  tempVariants.value.splice(index, 1)
}

async function saveGadgetAndVariants() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    if (isEditMode.value) {
      const resGadget = await fetch(`${API_URL}/gadgets/${newGadget.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          name: newGadget.value.name,
          description: newGadget.value.description,
          category: newGadget.value.category,
          min_donation: newGadget.value.min_donation,
          image_path: newGadget.value.image_path
        })
      })
      if (!resGadget.ok) {
        const errorData = await resGadget.json()
        throw new Error(errorData.detail || t('gadgets.errors.updateFailed'))
      }
      const resVariants = await fetch(`${API_URL}/gadgets/${newGadget.value.id}/variants`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(tempVariants.value.map(v => ({
          id: v.id || null,
          size: v.size,
          color: v.color,
          model: v.model,
          variant_type: v.variant_type,
          sku: v.sku,
          price_modifier: v.price_modifier,
          image_path: v.image_path
        })))
      })
      if (!resVariants.ok) {
        const errorData = await resVariants.json()
        throw new Error(errorData.detail || t('gadgets.errors.variantUpdateFailed'))
      }
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('gadgets.editSuccess'), life: 3000 })
    } else {
      const resGadget = await fetch(API_URL + "/gadgets/", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(newGadget.value)
      })
      if (!resGadget.ok) throw new Error(t('gadgets.errors.createFailed'))
      const createdGadget = await resGadget.json()
      const gadgetId = createdGadget.id
      for (const variant of tempVariants.value) {
        const resVariant = await fetch(API_URL + "/gadgets/variants", {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
          body: JSON.stringify({ gadget_id: gadgetId, ...variant })
        })
        if (!resVariant.ok) {
          toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgets.errors.variantCreateFailed', { sku: variant.sku }), life: 4000 })
        }
      }
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('gadgets.createSuccess'), life: 3000 })
    }
    showCreateWizard.value = false
    loadGadgets()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: err.message || t('gadgets.errors.generic'), life: 4000 })
  } finally {
    loading.value = false
    if (isEditMode.value && newGadget.value.id) {
      releaseLock(newGadget.value.id)
    }
  }
}

function confirmDelete(id, name) {
  const gadget = gadgets.value.find(g => g.id === id)
  if (gadget && gadget.variants.some(v => v.stock_quantity > 0)) {
    toast.add({
      severity: 'error',
      summary: t('gadgets.deleteBlocked'),
      detail: t('gadgets.errors.cannotDeleteWithStock', { name }),
      life: 5000
    })
    return
  }
  confirm.require({
    message: t('gadgets.confirmDeleteMessage', { name }),
    header: t('gadgets.confirmDeleteHeader'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('gadgets.confirmDeleteAccept'),
    rejectLabel: t('common.cancel'),
    acceptProps: { severity: 'danger' },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: async () => {
      try {
        const token = (await supabase.auth.getSession()).data.session?.access_token
        const res = await fetch(`${API_URL}/gadgets/${id}`, {
          method: 'DELETE',
          headers: { Authorization: `Bearer ${token}` }
        })
        if (res.ok) {
          toast.add({ severity: 'success', summary: t('common.deleted'), detail: t('gadgets.deleteSuccess'), life: 3000 })
          loadGadgets()
        } else {
          const errorMsg = res.status === 400 ? await res.text() : t('gadgets.errors.deleteFailed')
          toast.add({ severity: 'error', summary: t('common.error'), detail: errorMsg, life: 3000 })
        }
      } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgets.errors.connectionFailed'), life: 3000 })
      }
    }
  })
}

onMounted(() => {
  loadGadgets()
})
</script>

<template>
<div class="gadgets-container py-5 px-3">
  <!-- Header -->
  <div class="flex justify-content-between align-items-center mb-5">
    <div>
      <h2 class="font-bold text-3xl mb-1 text-900">{{ t('gadgets.title') }}</h2>
      <p class="text-secondary text-sm m-0">{{ t('gadgets.subtitle') }}</p>
    </div>
    <Button v-if="!showCreateWizard" :label="t('gadgets.newGadget')" icon="pi pi-plus" severity="primary" @click="startCreate" />
    <Button v-else :label="t('common.cancel')" icon="pi pi-times" severity="secondary" outlined @click="cancelEdit" />
  </div>

  <!-- Wizard Creazione -->
  <div v-if="showCreateWizard" class="card p-4 shadow-2 border-round surface-card mb-5">
    <h3 class="text-xl font-bold mb-4 text-primary">{{ isEditMode ? t('gadgets.wizard.editTitle') : t('gadgets.wizard.createTitle') }}</h3>
    <Stepper v-model:value="activeStep">
      <StepList class="mb-4">
        <Step value="1">{{ t('gadgets.wizard.step1') }}</Step>
        <Step value="2">{{ t('gadgets.wizard.step2') }}</Step>
        <Step value="3">{{ t('gadgets.wizard.step3') }}</Step>
      </StepList>
      <StepPanels>
        <!-- STEP 1 -->
        <StepPanel v-slot="{ activateCallback }" value="1">
          <div class="grid py-3 text-left">
            <div class="col-12 md:col-8 flex flex-column gap-4">
              <div class="flex flex-column gap-2">
                <label for="name" class="font-semibold text-sm">{{ t('gadgets.form.name') }} *</label>
                <InputText id="name" v-model="newGadget.name" :placeholder="t('gadgets.placeholders.name')" class="w-full" />
              </div>
              <div class="grid">
                <div class="col-12 md:col-6 flex flex-column gap-2">
                  <label id="category_label" class="font-semibold text-sm">{{ t('gadgets.form.category') }} *</label>
                  <Select aria-labelledby="category_label" v-model="newGadget.category" :options="categories" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                <div class="col-12 md:col-6 flex flex-column gap-2">
                  <label for="min_donation" class="font-semibold text-sm">{{ t('gadgets.form.minDonation') }} *</label>
                  <InputNumber inputId="min_donation" v-model="newGadget.min_donation" :min="0" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" />
                </div>
              </div>
              <div class="flex flex-column gap-2">
                <label for="description" class="font-semibold text-sm">{{ t('gadgets.form.description') }}</label>
                <InputText id="description" v-model="newGadget.description" :placeholder="t('gadgets.placeholders.description')" class="w-full" />
              </div>
            </div>
            <div class="col-12 md:col-4 flex flex-column align-items-center justify-content-center border-left-none md:border-left-1 border-light pl-0 md:pl-4 mt-4 md:mt-0">
              <label class="font-semibold text-sm mb-2 align-self-start md:align-self-center">{{ t('gadgets.form.image') }}</label>
              <ImageUpload v-model="newGadget.image_path" :label="t('gadgets.form.imageLabel')" />
            </div>
          </div>
          <div class="flex pt-4 justify-content-end border-top-1 border-light">
            <Button :label="t('common.next')" icon="pi pi-arrow-right" iconPos="right" :disabled="!newGadget.name || !newGadget.category || newGadget.min_donation === null" @click="activateCallback('2')" />
          </div>
        </StepPanel>

        <!-- STEP 2 -->
        <StepPanel v-slot="{ activateCallback }" value="2">
          <div class="grid py-3">
            <div class="col-12 lg:col-4 border-right-none lg:border-right-1 border-light pr-0 lg:pr-4">
              <h4 class="font-bold text-lg mb-3 text-700">{{ t('gadgets.variant.add') }}</h4>
              <div class="flex flex-column gap-3 text-left">
                <div class="flex flex-column gap-1">
                  <label for="v_size" class="text-xs font-semibold">{{ t('gadgets.variant.size') }}</label>
                  <InputText id="v_size" v-model="newVariant.size" :placeholder="t('gadgets.placeholders.size')" class="w-full" size="small" />
                </div>
                <div class="flex flex-column gap-1">
                  <label for="v_color" class="text-xs font-semibold">{{ t('gadgets.variant.color') }}</label>
                  <InputText id="v_color" v-model="newVariant.color" :placeholder="t('gadgets.placeholders.color')" class="w-full" size="small" />
                </div>
                <div class="flex flex-column gap-1">
                  <label id="v_model_label" class="text-xs font-semibold">{{ t('gadgets.variant.model') }}</label>
                  <Select aria-labelledby="v_model_label" v-model="newVariant.model" :options="modelOptions" optionLabel="label" optionValue="value" :placeholder="t('gadgets.placeholders.selectModel')" class="w-full" size="small" />
                </div>
                <div class="flex flex-column gap-1">
                  <label for="v_type" class="text-xs font-semibold">{{ t('gadgets.variant.type') }}</label>
                  <InputText id="v_type" v-model="newVariant.variant_type" :placeholder="t('gadgets.placeholders.variantType')" class="w-full" size="small" />
                </div>
                <div class="flex flex-column gap-1">
                  <label for="v_sku" class="text-xs font-semibold">{{ t('gadgets.variant.sku') }}</label>
                  <InputText id="v_sku" v-model="newVariant.sku" :placeholder="t('gadgets.placeholders.sku')" class="w-full" size="small" />
                </div>
                <div class="flex flex-column gap-1">
                  <label for="v_price" class="text-xs font-semibold">{{ t('gadgets.variant.priceModifier') }}</label>
                  <InputNumber inputId="v_price" v-model="newVariant.price_modifier" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" size="small" />
                </div>
                <div class="flex flex-column gap-1 align-items-center mb-2">
                  <label class="text-xs font-semibold align-self-start">{{ t('gadgets.variant.image') }}</label>
                  <ImageUpload v-model="newVariant.image_path" :label="t('gadgets.form.imageLabel')" />
                </div>
                <Button :label="t('gadgets.variant.addButton')" icon="pi pi-plus" severity="success" size="small" class="mt-2" @click="addTempVariant" />
              </div>
            </div>
            <div class="col-12 lg:col-8 pl-0 lg:pl-4 mt-4 lg:mt-0">
              <h4 class="font-bold text-lg mb-3 text-700">{{ t('gadgets.variant.list', { count: tempVariants.length }) }}</h4>
              <DataTable :value="tempVariants" class="p-datatable-sm" responsiveLayout="scroll" :emptyMessage="t('gadgets.variant.empty')">
                <Column :header="t('gadgets.variant.image')" class="w-4rem">
                  <template #body="slotProps">
                    <div class="flex align-items-center justify-content-center">
                      <ImageUpload v-model="slotProps.data.image_path" compact />
                    </div>
                  </template>
                </Column>
                <Column field="sku" :header="t('gadgets.variant.sku')">
                  <template #body="slotProps">
                    <InputText v-model="slotProps.data.sku" class="w-full" size="small" />
                  </template>
                </Column>
                <Column field="size" :header="t('gadgets.variant.size')">
                  <template #body="slotProps">
                    <InputText v-model="slotProps.data.size" class="w-full" size="small" />
                  </template>
                </Column>
                <Column field="color" :header="t('gadgets.variant.color')">
                  <template #body="slotProps">
                    <InputText v-model="slotProps.data.color" class="w-full" size="small" />
                  </template>
                </Column>
                <Column field="model" :header="t('gadgets.variant.model')">
                  <template #body="slotProps">
                    <Select v-model="slotProps.data.model" :options="modelOptions" optionLabel="label" optionValue="value" class="w-full" size="small" />
                  </template>
                </Column>
                <Column field="price_modifier" :header="t('gadgets.variant.priceModifier')">
                  <template #body="slotProps">
                    <InputNumber v-model="slotProps.data.price_modifier" :minFractionDigits="2" :maxFractionDigits="2" mode="currency" currency="EUR" locale="it-IT" class="w-full" size="small" />
                  </template>
                </Column>
                <Column :header="t('common.actions')">
                  <template #body="slotProps">
                    <Button icon="pi pi-trash" severity="danger" text rounded @click="removeTempVariant(slotProps.index)" />
                  </template>
                </Column>
              </DataTable>
            </div>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('common.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('1')" />
            <Button :label="t('common.next')" icon="pi pi-arrow-right" iconPos="right" :disabled="tempVariants.length === 0" @click="activateCallback('3')" />
          </div>
        </StepPanel>

        <!-- STEP 3 -->
        <StepPanel v-slot="{ activateCallback }" value="3">
          <div class="py-3 text-left">
            <h4 class="font-bold text-lg mb-3 text-700">{{ isEditMode ? t('gadgets.summary.editTitle') : t('gadgets.summary.createTitle') }}</h4>
            <div class="surface-ground p-4 border-round grid row-gap-3 mb-4">
              <div class="col-12 md:col-6 flex flex-column gap-1">
                <span class="text-xs font-semibold text-color-secondary uppercase">{{ t('gadgets.form.name') }}</span>
                <span class="text-base text-900 font-medium">{{ newGadget.name }}</span>
              </div>
              <div class="col-12 md:col-6 flex flex-column gap-1">
                <span class="text-xs font-semibold text-color-secondary uppercase">{{ t('gadgets.form.category') }}</span>
                <span class="text-base text-900 font-medium">{{ newGadget.category }}</span>
              </div>
              <div class="col-12 md:col-6 flex flex-column gap-1">
                <span class="text-xs font-semibold text-color-secondary uppercase">{{ t('gadgets.form.minDonation') }}</span>
                <span class="text-base text-primary font-bold">{{ newGadget.min_donation.toFixed(2) }} €</span>
              </div>
              <div class="col-12 md:col-6 flex flex-column gap-1">
                <span class="text-xs font-semibold text-color-secondary uppercase">{{ t('gadgets.form.description') }}</span>
                <span class="text-base text-900 font-medium">{{ newGadget.description || '-' }}</span>
              </div>
              <div class="col-12 flex flex-column gap-1 mt-2">
                <span class="text-xs font-semibold text-color-secondary uppercase">{{ t('gadgets.form.image') }}</span>
                <div class="border-round border-1 border-light overflow-hidden" style="width: 80px; height: 120px; background-color: var(--code-bg);">
                  <img v-if="newGadget.image_path" :src="getImageUrl(newGadget.image_path)" alt="Gadget" class="w-full h-full object-fit-cover" />
                  <div v-else class="w-full h-full flex align-items-center justify-content-center text-color-secondary"><i class="pi pi-image text-xl"></i></div>
                </div>
              </div>
            </div>
            <h4 class="font-bold text-lg mb-3 text-700">{{ isEditMode ? t('gadgets.summary.variantsModified') : t('gadgets.summary.variantsToCreate') }}</h4>
            <DataTable :value="tempVariants" class="p-datatable-sm" responsiveLayout="scroll">
              <Column field="sku" :header="t('gadgets.variant.sku')"></Column>
              <Column field="size" :header="t('gadgets.variant.size')"></Column>
              <Column field="color" :header="t('gadgets.variant.color')"></Column>
              <Column field="model" :header="t('gadgets.variant.model')"></Column>
              <Column field="price_modifier" :header="t('gadgets.summary.finalPrice')">
                <template #body="slotProps">
                  {{ (newGadget.min_donation + slotProps.data.price_modifier).toFixed(2) }} €
                </template>
              </Column>
            </DataTable>
          </div>
          <div class="flex pt-4 justify-content-between border-top-1 border-light">
            <Button :label="t('common.back')" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('2')" />
            <Button :label="isEditMode ? t('common.save') : t('gadgets.createButton')" icon="pi pi-check" severity="success" :loading="loading" @click="saveGadgetAndVariants" />
          </div>
        </StepPanel>
      </StepPanels>
    </Stepper>
  </div>

  <!-- Lista Gadget -->
  <div v-else class="card p-4 shadow-2 border-round surface-card">
    <DataTable :value="gadgets" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
      <template #empty>
        <div class="text-center py-4">
          <i class="pi pi-box text-4xl text-300 mb-2"></i>
          <p class="m-0 text-color-secondary">{{ t('gadgets.empty') }}</p>
        </div>
      </template>
      <Column :header="t('gadgets.table.image')" class="w-5rem text-center">
        <template #body="slotProps">
          <div class="flex align-items-center justify-content-center m-auto border-1 border-light border-round overflow-hidden" style="width: 40px; height: 60px; background-color: var(--code-bg);">
            <Image v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Gadget" preview imageClass="object-fit-cover" style="width: 100%; height: 100%;" />
            <i v-else class="pi pi-image text-color-secondary text-lg"></i>
          </div>
        </template>
      </Column>
      <Column field="name" :header="t('gadgets.table.name')" sortable class="font-bold"></Column>
      <Column field="category" :header="t('gadgets.table.category')" sortable>
        <template #body="slotProps">
          <span class="badge border-round px-2 py-1 text-xs bg-cyan-100 text-cyan-800">{{ slotProps.data.category }}</span>
        </template>
      </Column>
      <Column field="min_donation" :header="t('gadgets.table.minDonation')" sortable>
        <template #body="slotProps">{{ slotProps.data.min_donation.toFixed(2) }} €</template>
      </Column>
      <Column field="description" :header="t('gadgets.table.description')"></Column>
      <Column :header="t('gadgets.table.variants')">
        <template #body="slotProps">
          <div class="flex flex-wrap gap-2">
            <div v-for="v in slotProps.data.variants" :key="v.id" class="flex align-items-center gap-2 bg-light border-round px-2 py-1 text-xs" :title="`SKU: ${v.sku}`">
              <div class="flex align-items-center justify-content-center border-round overflow-hidden border-1 border-300" style="width: 16px; height: 24px; background-color: var(--code-bg);">
                <img v-if="v.image_path || slotProps.data.image_path" :src="getImageUrl(v.image_path || slotProps.data.image_path)" alt="Var" class="w-full h-full object-fit-cover" />
                <i v-else class="pi pi-image text-400" style="font-size: 8px;"></i>
              </div>
              <span>{{ v.size || '' }} {{ v.color || '' }} {{ v.model || '' }} <span :class="['font-semibold ml-1', v.stock_quantity < 1 ? 'text-red-500' : '']">({{ v.stock_quantity }} {{ t('gadgets.table.pcs') }})</span></span>
            </div>
          </div>
        </template>
      </Column>
      <Column field="total_stock" :header="t('gadgets.table.totalStock')" sortable>
        <template #body="slotProps">
          <span :class="['font-bold', slotProps.data.total_stock < 1 ? 'text-red-500' : 'text-900']">{{ slotProps.data.total_stock }} {{ t('gadgets.table.pcs') }}</span>
        </template>
      </Column>
      <Column :header="t('common.actions')">
        <template #body="slotProps">
          <div class="flex gap-2">
            <Button icon="pi pi-pencil" severity="secondary" outlined size="small" class="p-button-rounded" @click="startEdit(slotProps.data)" />
            <Button icon="pi pi-trash" severity="danger" outlined size="small" class="p-button-rounded" @click="confirmDelete(slotProps.data.id, slotProps.data.name)" />
          </div>
        </template>
      </Column>
    </DataTable>
  </div>
</div>
</template>

<style scoped>
.gadgets-container {
max-width: 1200px;
margin: 0 auto;
}
.surface-ground {
background-color: var(--code-bg);
}
.border-light {
border-color: var(--border);
}
:deep(.p-image-img) {
width: 100% !important;
height: 100% !important;
object-fit: cover !important;
}
.object-fit-cover {
object-fit: cover;
}
</style>