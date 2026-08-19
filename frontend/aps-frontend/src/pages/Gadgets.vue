<script setup>
import { API_URL, getImageUrl } from '../config.js'
import { ref, onMounted } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'
import ImageUpload from '../components/ImageUpload.vue'

import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'
import Select from 'primevue/select'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()

const gadgets = ref([])
const loading = ref(false)
const showCreateDialog = ref(false)
const isEditMode = ref(false)
let heartbeatInterval = null

const newGadget = ref({
  id: null,
  name: '',
  description: '',
  category: 'T-SHIRT',
  min_donation: 10.0,
  image_path: '',
  size: '',
  color: '',
  model: '',
  variant_type: '',
  sku: '',
  price_modifier: 0.0
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

async function loadGadgets() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/gadgets/", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      gadgets.value = data
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
  showCreateDialog.value = false
  if (isEditMode.value && newGadget.value.id) {
    releaseLock(newGadget.value.id)
  }
}

function startCreate() {
  isEditMode.value = false
  newGadget.value = {
    id: null,
    name: '',
    description: '',
    category: 'T-SHIRT',
    min_donation: 10.0,
    image_path: '',
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0
  }
  showCreateDialog.value = true
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
    image_path: gadget.image_path || '',
    size: gadget.size || '',
    color: gadget.color || '',
    model: gadget.model || '',
    variant_type: gadget.variant_type || '',
    sku: gadget.sku || '',
    price_modifier: gadget.price_modifier || 0.0
  }
  showCreateDialog.value = true
}

async function saveGadget() {
  if (!newGadget.value.sku) {
    const cat = newGadget.value.category.substring(0, 3)
    const rand = Math.floor(1000 + Math.random() * 9000)
    newGadget.value.sku = `${cat}-${newGadget.value.size || 'UNI'}-${newGadget.value.color || 'GEN'}-${rand}`.toUpperCase()
  }

  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    if (isEditMode.value) {
      const resGadget = await fetch(`${API_URL}/gadgets/${newGadget.value.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(newGadget.value)
      })
      if (!resGadget.ok) {
        const errorData = await resGadget.json()
        throw new Error(errorData.detail || t('gadgets.errors.updateFailed'))
      }
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('gadgets.editSuccess'), life: 3000 })
    } else {
      const resGadget = await fetch(API_URL + "/gadgets/", {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(newGadget.value)
      })
      if (!resGadget.ok) throw new Error(t('gadgets.errors.createFailed'))
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('gadgets.createSuccess'), life: 3000 })
    }
    showCreateDialog.value = false
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
  if (gadget && (gadget.stock_quantity || 0) > 0) {
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
  <div class="flex flex-column sm:flex-row justify-content-between align-items-start sm:align-items-center gap-3 mb-5">
    <div>
      <h2 class="font-bold text-3xl mb-1 text-900">{{ t('gadgets.title') }}</h2>
      <p class="text-secondary text-sm m-0">{{ t('gadgets.subtitle') }}</p>
    </div>
    <Button :label="t('gadgets.newGadget')" icon="pi pi-plus" severity="primary" @click="startCreate" class="w-full sm:w-auto" />
  </div>

  <!-- Dialog Creazione/Modifica -->
  <Dialog v-model:visible="showCreateDialog" :header="isEditMode ? t('gadgets.wizard.editTitle') : t('gadgets.wizard.createTitle')" :modal="true" style="width: 90vw; max-width: 800px;">
    <div class="grid py-2 text-left">
      <div class="col-12 md:col-8 flex flex-column gap-3">
        <div class="flex flex-column gap-1">
          <label for="name" class="font-semibold text-sm">{{ t('gadgets.form.name') }} *</label>
          <InputText id="name" v-model="newGadget.name" :placeholder="t('gadgets.placeholders.name')" class="w-full" />
        </div>
        <div class="grid">
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label id="category_label" class="font-semibold text-sm">{{ t('gadgets.form.category') }} *</label>
            <Select aria-labelledby="category_label" v-model="newGadget.category" :options="categories" optionLabel="label" optionValue="value" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="min_donation" class="font-semibold text-sm">{{ t('gadgets.form.minDonation') }} *</label>
            <InputNumber inputId="min_donation" v-model="newGadget.min_donation" :min="0" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" />
          </div>
        </div>
        <div class="flex flex-column gap-1">
          <label for="description" class="font-semibold text-sm">{{ t('gadgets.form.description') }}</label>
          <InputText id="description" v-model="newGadget.description" :placeholder="t('gadgets.placeholders.description')" class="w-full" />
        </div>
        
        <!-- Caratteristiche dell'articolo -->
        <h4 class="font-bold text-md mt-3 mb-1 text-700">Caratteristiche Articolo</h4>
        <div class="grid">
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="sku" class="font-semibold text-xs">{{ t('gadgets.variant.sku') }}</label>
            <InputText id="sku" v-model="newGadget.sku" :placeholder="t('gadgets.placeholders.sku')" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="size" class="font-semibold text-xs">{{ t('gadgets.variant.size') }}</label>
            <InputText id="size" v-model="newGadget.size" :placeholder="t('gadgets.placeholders.size')" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="color" class="font-semibold text-xs">{{ t('gadgets.variant.color') }}</label>
            <InputText id="color" v-model="newGadget.color" :placeholder="t('gadgets.placeholders.color')" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label id="model_label" class="font-semibold text-xs">{{ t('gadgets.variant.model') }}</label>
            <Select aria-labelledby="model_label" v-model="newGadget.model" :options="modelOptions" optionLabel="label" optionValue="value" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="variant_type" class="font-semibold text-xs">{{ t('gadgets.variant.type') }}</label>
            <InputText id="variant_type" v-model="newGadget.variant_type" :placeholder="t('gadgets.placeholders.variantType')" class="w-full" />
          </div>
          <div class="col-12 md:col-6 flex flex-column gap-1">
            <label for="price_modifier" class="font-semibold text-xs">{{ t('gadgets.variant.priceModifier') }}</label>
            <InputNumber inputId="price_modifier" v-model="newGadget.price_modifier" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" />
          </div>
        </div>
      </div>

      <div class="col-12 md:col-4 flex flex-column align-items-center border-left-none md:border-left-1 border-light pl-0 md:pl-4 mt-4 md:mt-0">
        <label class="font-semibold text-sm mb-2 align-self-start md:align-self-center">{{ t('gadgets.form.image') }}</label>
        <ImageUpload v-model="newGadget.image_path" :label="t('gadgets.form.imageLabel')" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="cancelEdit" />
      <Button :label="isEditMode ? t('common.save') : t('gadgets.createButton')" icon="pi pi-check" severity="success" :loading="loading" :disabled="!newGadget.name || !newGadget.category || newGadget.min_donation === null" @click="saveGadget" />
    </template>
  </Dialog>

  <!-- Lista Gadget -->
  <div class="card p-4 shadow-2 border-round surface-card">
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
            <img v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Gadget" class="w-full h-full object-fit-cover" />
            <i v-else class="pi pi-image text-color-secondary text-lg"></i>
          </div>
        </template>
      </Column>
      <Column field="sku" header="SKU" sortable class="font-medium text-sm"></Column>
      <Column field="name" :header="t('gadgets.table.name')" sortable class="font-bold"></Column>
      <Column field="category" :header="t('gadgets.table.category')" sortable>
        <template #body="slotProps">
          <span class="badge border-round px-2 py-1 text-xs bg-cyan-100 text-cyan-800">{{ slotProps.data.category }}</span>
        </template>
      </Column>
      <Column header="Dettagli">
        <template #body="slotProps">
          <span class="text-xs text-secondary">
            {{ [slotProps.data.size, slotProps.data.color, slotProps.data.model, slotProps.data.variant_type].filter(Boolean).join(' | ') || '-' }}
          </span>
        </template>
      </Column>
      <Column field="min_donation" :header="t('gadgets.table.minDonation')" sortable>
        <template #body="slotProps">
          {{ (slotProps.data.min_donation + (slotProps.data.price_modifier || 0)).toFixed(2) }} €
        </template>
      </Column>
      <Column field="stock_quantity" :header="t('gadgets.table.totalStock')" sortable>
        <template #body="slotProps">
          <span :class="['font-bold', (slotProps.data.stock_quantity || 0) < 1 ? 'text-red-500' : 'text-900']">{{ slotProps.data.stock_quantity || 0 }} {{ t('gadgets.table.pcs') }}</span>
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
.object-fit-cover {
  object-fit: cover;
}
</style>


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