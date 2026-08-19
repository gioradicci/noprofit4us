<script setup>
import { API_URL, getImageUrl } from '../config.js'
import { ref, onMounted, computed, watch } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { FilterMatchMode } from '@primevue/core/api'

import Button from 'primevue/button'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import Card from 'primevue/card'
import Image from 'primevue/image'

const { t } = useI18n()
const toast = useToast()

const gadgets = ref([])
const warehouses = ref([])
const movements = ref([])
const loading = ref(false)
const showMovementDialog = ref(false)
const submitting = ref(false)
const exporting = ref(false)

const filters = ref({
  gadget_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  category: { value: null, matchMode: FilterMatchMode.CONTAINS },
  sku: { value: null, matchMode: FilterMatchMode.CONTAINS },
  variant_details: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const movementFilters = ref({
  movement_type: { value: null, matchMode: FilterMatchMode.EQUALS },
  gadget_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  notes: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const movementForm = ref({
  gadget_id: null,
  movement_type: 'RESTOCK',
  from_warehouse_id: null,
  to_warehouse_id: null,
  quantity: 1,
  notes: ''
})

const movementTypes = [
  { label: t('gadgetStock.movementTypes.restock'), value: 'RESTOCK' },
  { label: t('gadgetStock.movementTypes.transfer'), value: 'TRANSFER' },
  { label: t('gadgetStock.movementTypes.delivery'), value: 'DELIVERY' }
]

const movementTypeFilterOptions = computed(() => [
  { label: t('gadgetStock.allTypes'), value: null },
  ...movementTypes
])

const gadgetOptions = computed(() => {
  return gadgets.value.map(g => ({
    label: `${g.name} ${g.sku ? `[SKU: ${g.sku}]` : ''} (${t('gadgetStock.stock')}: ${g.stock_quantity || 0})`,
    value: g.id,
    sku: g.sku,
    stocks: g.stocks
  }))
})

const fromWarehouseOptions = computed(() => {
  if (!movementForm.value.gadget_id) return []
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget || !gadget.stocks) return []
  const options = []
  gadget.stocks.forEach(stock => {
    if (stock.quantity > 0) {
      const wh = warehouses.value.find(w => w.id === stock.warehouse_id)
      if (wh) {
        options.push({
          label: `${wh.name} (${stock.quantity} ${t('gadgetStock.pcs')})${wh.is_active === false ? ` [${t('gadgetStock.disabled')}]` : ''}`,
          value: wh.id,
          quantity: stock.quantity
        })
      }
    }
  })
  return options
})

const toWarehouseOptions = computed(() => {
  if (!warehouses.value) return []
  const activeWarehouses = warehouses.value.filter(w => w.is_active !== false)
  if (!movementForm.value.gadget_id) {
    return activeWarehouses.map(w => ({
      label: `${w.name} (0 ${t('gadgetStock.pcs')})`,
      value: w.id,
      quantity: 0
    }))
  }
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget || !gadget.stocks) return []
  return activeWarehouses.map(w => {
    const stock = gadget.stocks.find(s => s.warehouse_id === w.id)
    const quantity = stock ? stock.quantity : 0
    return {
      label: `${w.name} (${quantity} ${t('gadgetStock.pcs')})`,
      value: w.id,
      quantity: quantity
    }
  })
})

const flattenedStocks = computed(() => {
  return gadgets.value.map(g => {
    const stockMap = {}
    warehouses.value.forEach(w => {
      const found = (g.stocks || []).find(s => s.warehouse_id === w.id)
      stockMap[w.code] = found ? found.quantity : 0
    })
    const parts = []
    if (g.size) parts.push(`${t('gadgetStock.size')}: ${g.size}`)
    if (g.color) parts.push(`${t('gadgetStock.color')}: ${g.color}`)
    if (g.model) parts.push(`${t('gadgetStock.model')}: ${g.model}`)
    const variant_details = parts.join(' | ') || '-'
    return {
      id: g.id,
      gadget_name: g.name,
      category: g.category,
      sku: g.sku,
      size: g.size,
      color: g.color,
      model: g.model,
      variant_details,
      total_stock: g.stock_quantity || 0,
      image_path: g.image_path || '',
      ...stockMap
    }
  })
})

const selectedGadgetImage = computed(() => {
  if (!movementForm.value.gadget_id) return null
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  return gadget ? gadget.image_path : null
})

const selectedGadgetName = computed(() => {
  if (!movementForm.value.gadget_id) return ''
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  return gadget ? gadget.name : ''
})

const selectedGadgetDetails = computed(() => {
  if (!movementForm.value.gadget_id) return ''
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget) return ''
  const parts = []
  if (gadget.sku) parts.push(`SKU: ${gadget.sku}`)
  if (gadget.size) parts.push(`${t('gadgetStock.size')}: ${gadget.size}`)
  if (gadget.color) parts.push(`${t('gadgetStock.color')}: ${gadget.color}`)
  if (gadget.model) parts.push(`${t('gadgetStock.model')}: ${gadget.model}`)
  return parts.join(' | ')
})

const totalStockPieces = computed(() => {
  return flattenedStocks.value.reduce((acc, curr) => acc + curr.total_stock, 0)
})

watch(() => movementForm.value.gadget_id, () => {
  movementForm.value.from_warehouse_id = null
  movementForm.value.to_warehouse_id = null
})

watch(() => movementForm.value.movement_type, (newType) => {
  if (newType === 'RESTOCK') {
    movementForm.value.from_warehouse_id = null
  } else if (newType === 'DELIVERY') {
    movementForm.value.to_warehouse_id = null
  }
})

async function loadData() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const headers = { Authorization: `Bearer ${token}` }
    const resGadgets = await fetch(API_URL + "/gadgets/", { headers })
    if (resGadgets.ok) gadgets.value = await resGadgets.json()
    const resWarehouses = await fetch(API_URL + "/gadgets/warehouses", { headers })
    if (resWarehouses.ok) warehouses.value = await resWarehouses.json()
    const resMovements = await fetch(API_URL + "/gadgets/movements", { headers })
    if (resMovements.ok) movements.value = await resMovements.json()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.loadFailed'), life: 3000 })
  } finally {
    loading.value = false
  }
}

function openMovementModal() {
  movementForm.value = {
    gadget_id: null,
    movement_type: 'RESTOCK',
    from_warehouse_id: null,
    to_warehouse_id: null,
    quantity: 1,
    notes: ''
  }
  showMovementDialog.value = true
}

async function submitMovement() {
  if (!movementForm.value.gadget_id || !movementForm.value.quantity) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.requiredFields'), life: 3000 })
    return
  }
  if (movementForm.value.movement_type === 'TRANSFER') {
    if (!movementForm.value.from_warehouse_id || !movementForm.value.to_warehouse_id) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.selectBothWarehouses'), life: 3000 })
      return
    }
    if (movementForm.value.from_warehouse_id === movementForm.value.to_warehouse_id) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.differentWarehouses'), life: 4000 })
      return
    }
  }
  if (movementForm.value.movement_type === 'RESTOCK' && !movementForm.value.to_warehouse_id) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.selectDestination'), life: 3000 })
    return
  }
  if (movementForm.value.movement_type === 'DELIVERY' && !movementForm.value.from_warehouse_id) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.selectSource'), life: 3000 })
    return
  }
  if (movementForm.value.movement_type !== 'RESTOCK') {
    const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
    const sourceStock = gadget?.stocks?.find(s => s.warehouse_id === movementForm.value.from_warehouse_id)?.quantity || 0
    if (sourceStock < movementForm.value.quantity) {
      toast.add({ severity: 'error', summary: t('gadgetStock.errors.insufficientStock'), detail: t('gadgetStock.errors.insufficientStockDetail', { stock: sourceStock }), life: 4000 })
      return
    }
  }
  submitting.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/gadgets/movements", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        gadget_id: movementForm.value.gadget_id,
        from_warehouse_id: movementForm.value.from_warehouse_id,
        to_warehouse_id: movementForm.value.to_warehouse_id,
        quantity: movementForm.value.quantity,
        movement_type: movementForm.value.movement_type,
        notes: movementForm.value.notes
      })
    })
    if (res.ok) {
      toast.add({ severity: 'success', summary: t('gadgetStock.registered'), detail: t('gadgetStock.movementSuccess'), life: 3000 })
      showMovementDialog.value = false
      loadData()
    } else {
      const errDetail = await res.json()
      toast.add({ severity: 'error', summary: t('common.error'), detail: errDetail.detail || t('gadgetStock.errors.movementFailed'), life: 4000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.connectionFailed'), life: 3000 })
  } finally {
    submitting.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('it-IT')
}

async function exportInventory() {
  exporting.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + "/gadgets/export-inventory", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'inventario_gadget.xlsx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.add({ severity: 'success', summary: t('gadgetStock.exported'), detail: t('gadgetStock.exportSuccess'), life: 3000 })
    } else {
      console.error("Errore durante l'esportazione", await res.text())
      toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.exportFailed'), life: 4000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.connectionFailed'), life: 3000 })
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
<div class="stock-container py-5 px-3">
  <!-- Header -->
  <div class="flex flex-column sm:flex-row justify-content-between align-items-start sm:align-items-center gap-3 mb-5">
    <div>
      <h2 class="font-bold text-3xl mb-1 text-900">{{ t('gadgetStock.title') }}</h2>
      <p class="text-secondary text-sm m-0">{{ t('gadgetStock.subtitle') }}</p>
    </div>
    <div class="flex flex-column sm:flex-row gap-2 w-full sm:w-auto">
      <Button :label="t('gadgetStock.exportInventory')" icon="pi pi-download" severity="secondary" outlined @click="exportInventory" :loading="exporting" class="w-full sm:w-auto" />
      <Button :label="t('gadgetStock.registerMovement')" icon="pi pi-directions" severity="primary" @click="openMovementModal" class="w-full sm:w-auto" />
    </div>
  </div>

  <!-- KPIs -->
  <div class="flex flex-wrap gap-4 justify-content-between mb-5">
    <div class="flex-1 min-w-12rem">
      <Card class="shadow-1">
        <template #content>
          <div class="text-center">
            <div class="text-3xl font-bold text-primary">{{ totalStockPieces }}</div>
            <div class="text-sm text-secondary uppercase font-semibold mt-1">{{ t('gadgetStock.totalStockPieces') }}</div>
          </div>
        </template>
      </Card>
    </div>
    <div class="flex-1 min-w-12rem">
      <Card class="shadow-1">
        <template #content>
          <div class="text-center">
            <div class="text-3xl font-bold text-cyan-600">{{ movements.length }}</div>
            <div class="text-sm text-secondary uppercase font-semibold mt-1">{{ t('gadgetStock.registeredMovements') }}</div>
          </div>
        </template>
      </Card>
    </div>
    <div class="flex-1 min-w-12rem">
      <Card class="shadow-1">
        <template #content>
          <div class="text-center">
            <div class="text-3xl font-bold text-orange-500">{{ warehouses.length }}</div>
            <div class="text-sm text-secondary uppercase font-semibold mt-1">{{ t('gadgetStock.activeWarehouses') }}</div>
          </div>
        </template>
      </Card>
    </div>
  </div>

  <!-- Main Content -->
  <div class="grid">
    <!-- Stocks Table -->
    <div class="col-12 mb-5">
      <div class="card p-4 shadow-2 border-round surface-card">
        <h3 class="text-xl font-bold mb-4 text-900">Giacenze per Gadget</h3>
        <DataTable :value="flattenedStocks" v-model:filters="filters" filterDisplay="row" :loading="loading" paginator :rows="10" scrollable responsiveLayout="scroll">
          <template #empty>
            <div class="text-center py-4">
              <i class="pi pi-info-circle text-3xl text-400 mb-2"></i>
              <p class="m-0 text-color-secondary">{{ t('gadgetStock.noData') }}</p>
            </div>
          </template>
          <Column frozen :header="t('gadgetStock.photo')" class="w-5rem text-center" style="min-width: 60px">
            <template #body="slotProps">
              <div class="flex align-items-center justify-content-center m-auto border-1 border-light border-round overflow-hidden" style="width: 40px; height: 60px; background-color: var(--code-bg);">
                <img v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Gadget" class="w-full h-full object-fit-cover" />
                <i v-else class="pi pi-image text-color-secondary text-lg"></i>
              </div>
            </template>
          </Column>
          <Column field="gadget_name" :header="t('gadgetStock.gadget')" sortable class="font-bold" filter filterField="gadget_name" :showFilterMenu="false" :showClearButton="true">
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchGadget')" class="w-full" />
            </template>
          </Column>
          <Column field="variant_details" :header="t('gadgetStock.variantDetails')" filter filterField="variant_details" :showFilterMenu="false" :showClearButton="true">
            <template #body="slotProps"><span class="text-sm">{{ slotProps.data.variant_details }}</span></template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchDetails')" class="w-full" />
            </template>
          </Column>
          <Column field="category" :header="t('gadgetStock.category')" sortable filter filterField="category" :showFilterMenu="false" :showClearButton="true">
            <template #body="slotProps">
              <span class="badge border-round px-2 py-1 text-xs bg-cyan-100 text-cyan-800">{{ slotProps.data.category }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchCategory')" class="w-full" />
            </template>
          </Column>
          <Column field="sku" :header="t('gadgetStock.sku')" sortable filter filterField="sku" :showFilterMenu="false" :showClearButton="true">
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchSku')" class="w-full" />
            </template>
          </Column>
          <Column field="total_stock" :header="t('gadgetStock.totalStock')" sortable class="bg-surface-50">
            <template #body="slotProps">
              <span :class="['font-bold', slotProps.data.total_stock < 1 ? 'text-red-500' : 'text-primary']">{{ slotProps.data.total_stock }} {{ t('gadgetStock.pcs') }}</span>
            </template>
          </Column>
          <Column v-for="wh in warehouses.filter(w => w.is_active !== false)" :key="wh.id" :field="wh.code" :header="wh.name" sortable>
            <template #body="slotProps">
              <span :class="['font-bold', slotProps.data[wh.code] > 0 ? 'text-green-600' : 'text-400']">{{ slotProps.data[wh.code] }} {{ t('gadgetStock.pcs') }}</span>
            </template>
          </Column>
        </DataTable>
      </div>
    </div>

    <!-- Movement History -->
    <div class="col-12">
      <div class="card p-4 shadow-2 border-round surface-card">
        <h3 class="text-xl font-bold mb-4 text-900">{{ t('gadgetStock.movementHistory') }}</h3>
        <DataTable :value="movements" v-model:filters="movementFilters" filterDisplay="row" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
          <template #empty>
            <div class="text-center py-4">
              <i class="pi pi-history text-3xl text-400 mb-2"></i>
              <p class="m-0 text-color-secondary">{{ t('gadgetStock.noMovements') }}</p>
            </div>
          </template>
          <Column :header="t('gadgetStock.photo')" class="w-5rem text-center">
            <template #body="slotProps">
              <div class="flex align-items-center justify-content-center m-auto border-1 border-light border-round overflow-hidden" style="width: 40px; height: 60px; background-color: var(--code-bg);">
                <img v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Movimento" class="w-full h-full object-fit-cover" />
                <i v-else class="pi pi-image text-color-secondary text-lg"></i>
              </div>
            </template>
          </Column>
          <Column field="timestamp" :header="t('gadgetStock.dateTime')" sortable>
            <template #body="slotProps">{{ formatDate(slotProps.data.timestamp) }}</template>
          </Column>
          <Column field="movement_type" :header="t('gadgetStock.type')" sortable filter filterField="movement_type" :showFilterMenu="false" :showClearButton="true">
            <template #body="slotProps">
              <span :class="['badge border-round px-2 py-1 text-xs text-white font-bold', slotProps.data.movement_type === 'RESTOCK' ? 'bg-green-500' : slotProps.data.movement_type === 'TRANSFER' ? 'bg-blue-500' : 'bg-orange-500']">{{ slotProps.data.movement_type }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <Select v-model="filterModel.value" @change="filterCallback()" :options="movementTypeFilterOptions" optionLabel="label" optionValue="value" :placeholder="t('gadgetStock.filterType')" class="w-full" />
            </template>
          </Column>
          <Column field="gadget_name" :header="t('gadgetStock.gadget')" sortable filter filterField="gadget_name" :showFilterMenu="false" :showClearButton="true">
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchGadget')" class="w-full" />
            </template>
          </Column>
          <Column field="gadget_sku" :header="t('gadgetStock.sku')"></Column>
          <Column :header="t('gadgetStock.path')">
            <template #body="slotProps">
              <span class="text-sm">
                {{ slotProps.data.from_warehouse ? slotProps.data.from_warehouse.name : t('gadgetStock.external') }}
                <i class="pi pi-arrow-right text-xs mx-2"></i>
                {{ slotProps.data.to_warehouse ? slotProps.data.to_warehouse.name : t('gadgetStock.deliveredToMember') }}
              </span>
            </template>
          </Column>
          <Column field="quantity" :header="t('gadgetStock.quantity')">
            <template #body="slotProps"><span class="font-bold">{{ slotProps.data.quantity }} {{ t('gadgetStock.pcs') }}</span></template>
          </Column>
          <Column field="notes" :header="t('gadgetStock.notes')" filter filterField="notes" :showFilterMenu="false" :showClearButton="true">
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchNotes')" class="w-full" />
            </template>
          </Column>
        </DataTable>
      </div>
    </div>
  </div>

  <!-- Movement Dialog -->
  <Dialog v-model:visible="showMovementDialog" :header="t('gadgetStock.movementDialogTitle')" :modal="true" :style="{ width: '500px' }">
    <div class="flex flex-column gap-4 py-2 text-left">
      <div class="flex flex-column gap-2">
        <label for="m_gadget" class="font-semibold text-sm">{{ t('gadgetStock.form.gadget') }} *</label>
        <Select inputId="m_gadget" v-model="movementForm.gadget_id" :options="gadgetOptions" optionLabel="label" optionValue="value" :placeholder="t('gadgetStock.form.selectGadget')" class="w-full" />
      </div>
      <div v-if="movementForm.gadget_id" class="flex align-items-center gap-3 p-3 border-round" style="background-color: var(--code-bg); border: 1px solid var(--border);">
        <div class="border-round border-1 border-light overflow-hidden flex align-items-center justify-content-center" style="width: 40px; height: 60px; background-color: var(--bg); flex-shrink: 0;">
          <img v-if="selectedGadgetImage" :src="getImageUrl(selectedGadgetImage)" alt="Preview" class="w-full h-full object-fit-cover" />
          <i v-else class="pi pi-image text-color-secondary text-lg"></i>
        </div>
        <div class="flex flex-column gap-1 text-left">
          <span class="text-xxs font-semibold text-color-secondary uppercase" style="letter-spacing: 0.5px;">{{ t('gadgetStock.form.selectedItem') }}</span>
          <span class="text-sm font-bold text-900 line-height-2">{{ selectedGadgetName }}</span>
          <span class="text-xs text-500 font-medium">{{ selectedGadgetDetails }}</span>
        </div>
      </div>
      <div class="flex flex-column gap-2">
        <label for="m_type" class="font-semibold text-sm">{{ t('gadgetStock.form.movementType') }} *</label>
        <Select inputId="m_type" v-model="movementForm.movement_type" :options="movementTypes" optionLabel="label" optionValue="value" class="w-full" />
      </div>
      <div class="flex flex-column gap-2" v-if="['TRANSFER', 'DELIVERY'].includes(movementForm.movement_type)">
        <label for="m_from" class="font-semibold text-sm">{{ t('gadgetStock.form.sourceWarehouse') }} *</label>
        <Select inputId="m_from" v-model="movementForm.from_warehouse_id" :options="fromWarehouseOptions.filter(opt => opt.value !== movementForm.to_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.gadget_id ? t('gadgetStock.form.selectSource') : 'Seleziona prima un gadget'" :disabled="!movementForm.gadget_id" class="w-full" />
      </div>
      <div class="flex flex-column gap-2" v-if="['RESTOCK', 'TRANSFER'].includes(movementForm.movement_type)">
        <label for="m_to" class="font-semibold text-sm">{{ t('gadgetStock.form.destinationWarehouse') }} *</label>
        <Select inputId="m_to" v-model="movementForm.to_warehouse_id" :options="toWarehouseOptions.filter(opt => opt.value !== movementForm.from_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.gadget_id ? t('gadgetStock.form.selectDestination') : 'Seleziona prima un gadget'" :disabled="!movementForm.gadget_id" class="w-full" />
      </div>
      <div class="flex flex-column gap-2">
        <label for="m_qty" class="font-semibold text-sm">{{ t('gadgetStock.form.quantity') }} *</label>
        <InputNumber inputId="m_qty" v-model="movementForm.quantity" :min="1" :placeholder="t('gadgetStock.form.quantityPlaceholder')" class="w-full" showButtons />
      </div>
      <div class="flex flex-column gap-2">
        <label for="m_notes" class="font-semibold text-sm">{{ t('gadgetStock.form.notes') }}</label>
        <InputText id="m_notes" v-model="movementForm.notes" :placeholder="t('gadgetStock.form.notesPlaceholder')" class="w-full" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="showMovementDialog = false" />
      <Button :label="t('gadgetStock.form.register')" severity="success" :loading="submitting" @click="submitMovement" />
    </template>
  </Dialog>
</div>
</template>

<style scoped>
.stock-container {
  max-width: 1200px;
  margin: 0 auto;
}
.border-light {
  border-color: var(--border);
}
.object-fit-cover {
  object-fit: cover;
}
.line-height-2 {
  line-height: 1.2;
}
.text-xxs {
  font-size: 0.65rem;
}
</style>