<script setup>
import { API_URL } from '../config.js'
import { ref, onMounted } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'

import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputSwitch from 'primevue/inputswitch'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'

const { t } = useI18n()
const toast = useToast()

const warehouses = ref([])
const loading = ref(false)
const showDialog = ref(false)
const editingWarehouse = ref(null)
const saving = ref(false)

const form = ref({
  name: '',
  code: '',
  address: '',
  is_active: true
})

async function loadWarehouses() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/gadgets/warehouses", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      warehouses.value = await res.json()
    } else {
      toast.add({ severity: 'error', summary: t('common.error'), detail: t('warehouses.errors.loadFailed'), life: 3000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('warehouses.errors.connectionFailed'), life: 3000 })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingWarehouse.value = null
  form.value = { name: '', code: '', address: '', is_active: true }
  showDialog.value = true
}

function openEdit(warehouse) {
  editingWarehouse.value = warehouse
  form.value = {
    name: warehouse.name,
    code: warehouse.code,
    address: warehouse.address || '',
    is_active: warehouse.is_active !== false
  }
  showDialog.value = true
}

async function saveWarehouse() {
  if (!form.value.name || !form.value.code) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('warehouses.errors.requiredFields'), life: 3000 })
    return
  }
  saving.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const url = editingWarehouse.value
      ? `${API_URL}/gadgets/warehouses/${editingWarehouse.value.id}`
      : `${API_URL}/gadgets/warehouses`
    const method = editingWarehouse.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(form.value)
    })
    if (res.ok) {
      toast.add({
        severity: 'success',
        summary: t('common.success'),
        detail: editingWarehouse.value ? t('warehouses.editSuccess') : t('warehouses.createSuccess'),
        life: 3000
      })
      showDialog.value = false
      loadWarehouses()
    } else {
      const err = await res.json()
      toast.add({ severity: 'error', summary: t('common.error'), detail: err.detail || t('warehouses.errors.saveFailed'), life: 4000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('warehouses.errors.connectionFailed'), life: 3000 })
  } finally {
    saving.value = false
  }
}

async function toggleActive(warehouse) {
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(`${API_URL}/gadgets/warehouses/${warehouse.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ is_active: !warehouse.is_active })
    })
    if (res.ok) {
      warehouse.is_active = !warehouse.is_active
      toast.add({
        severity: 'success',
        summary: t('common.success'),
        detail: warehouse.is_active ? t('warehouses.activated') : t('warehouses.deactivated'),
        life: 3000
      })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('warehouses.errors.toggleFailed'), life: 3000 })
  }
}

onMounted(() => {
  loadWarehouses()
})
</script>

<template>
<div class="warehouses-container py-5 px-3">
  <!-- Header -->
  <div class="flex flex-column sm:flex-row justify-content-between align-items-start sm:align-items-center gap-3 mb-5">
    <div>
      <h2 class="font-bold text-3xl mb-1 text-900">{{ t('warehouses.title') }}</h2>
      <p class="text-secondary text-sm m-0">{{ t('warehouses.subtitle') }}</p>
    </div>
    <Button :label="t('warehouses.newWarehouse')" icon="pi pi-plus" severity="primary" @click="openCreate" class="w-full sm:w-auto" />
  </div>

  <!-- Warehouse List -->
  <div class="card p-4 shadow-2 border-round surface-card">
    <DataTable :value="warehouses" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
      <template #empty>
        <div class="text-center py-4">
          <i class="pi pi-warehouse text-4xl text-300 mb-2"></i>
          <p class="m-0 text-color-secondary">{{ t('warehouses.empty') }}</p>
        </div>
      </template>
      <Column field="name" :header="t('warehouses.name')" sortable class="font-bold"></Column>
      <Column field="code" :header="t('warehouses.code')" sortable></Column>
      <Column field="address" :header="t('warehouses.address')">
        <template #body="slotProps">{{ slotProps.data.address || '-' }}</template>
      </Column>
      <Column :header="t('warehouses.active')" class="w-10rem">
        <template #body="slotProps">
          <div class="flex align-items-center gap-2">
            <InputSwitch :modelValue="slotProps.data.is_active !== false" @update:modelValue="toggleActive(slotProps.data)" />
            <span :class="['text-sm font-semibold', slotProps.data.is_active !== false ? 'text-green-600' : 'text-red-500']">
              {{ slotProps.data.is_active !== false ? t('warehouses.active') : t('warehouses.inactive') }}
            </span>
          </div>
        </template>
      </Column>
      <Column :header="t('common.actions')" class="w-10rem">
        <template #body="slotProps">
          <Button icon="pi pi-pencil" severity="secondary" outlined size="small" class="p-button-rounded" @click="openEdit(slotProps.data)" />
        </template>
      </Column>
    </DataTable>
  </div>

  <!-- Warehouse Dialog -->
  <Dialog v-model:visible="showDialog" :header="editingWarehouse ? t('warehouses.editWarehouse') : t('warehouses.newWarehouse')" :modal="true" :style="{ width: '450px' }">
    <div class="flex flex-column gap-4 py-2 text-left">
      <div class="flex flex-column gap-2">
        <label for="wh_name" class="font-semibold text-sm">{{ t('warehouses.form.name') }} *</label>
        <InputText id="wh_name" v-model="form.name" :placeholder="t('warehouses.placeholders.name')" class="w-full" />
      </div>
      <div class="flex flex-column gap-2">
        <label for="wh_code" class="font-semibold text-sm">{{ t('warehouses.form.code') }} *</label>
        <InputText id="wh_code" v-model="form.code" :placeholder="t('warehouses.placeholders.code')" class="w-full uppercase" />
      </div>
      <div class="flex flex-column gap-2">
        <label for="wh_address" class="font-semibold text-sm">{{ t('warehouses.form.address') }}</label>
        <InputText id="wh_address" v-model="form.address" :placeholder="t('warehouses.placeholders.address')" class="w-full" />
      </div>
      <div class="flex align-items-center gap-3">
        <label for="wh_active" class="font-semibold text-sm">{{ t('warehouses.form.active') }}</label>
        <InputSwitch id="wh_active" v-model="form.is_active" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="showDialog = false" />
      <Button :label="t('common.save')" severity="success" :loading="saving" @click="saveWarehouse" />
    </template>
  </Dialog>
</div>
</template>

<style scoped>
.warehouses-container {
max-width: 1200px;
margin: 0 auto;
}
</style>