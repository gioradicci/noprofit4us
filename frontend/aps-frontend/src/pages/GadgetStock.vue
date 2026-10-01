<script setup>
import { API_URL, getImageUrl } from '../config.js'
import { ref, onMounted, computed, watch } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useI18n } from 'vue-i18n'
import { useUser } from '../composables/useUser'
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
const { isAdminOrSecretary } = useUser()
const toast = useToast()

const gadgets = ref([])
const warehouses = ref([])
const movements = ref([])
const loans = ref([])
const loanAssignees = ref([])
const loading = ref(false)
const showMovementDialog = ref(false)
const showReturnDialog = ref(false)
const showOnlyActiveLoans = ref(true)
const submitting = ref(false)
const returningSubmitting = ref(false)
const exporting = ref(false)

const selectedLoan = ref(null)
const returnForm = ref({
  returned_quantity: 1,
  to_warehouse_id: null,
  notes: ''
})

const filters = ref({
  gadget_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  category: { value: null, matchMode: FilterMatchMode.CONTAINS },
  sku: { value: null, matchMode: FilterMatchMode.CONTAINS },
  variant_details: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const movementFilters = ref({
  movement_type: { value: null, matchMode: FilterMatchMode.EQUALS },
  gadget_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  notes: { value: null, matchMode: FilterMatchMode.CONTAINS },
  performed_by_display: { value: null, matchMode: FilterMatchMode.CONTAINS }
})

const movementForm = ref({
  gadget_id: null,
  movement_type: 'RESTOCK',
  from_warehouse_id: null,
  to_warehouse_id: null,
  quantity: 1,
  notes: '',
  assigned_to_user_id: null,
  assigned_to_name: '',
  expected_return_date: null,
  loan_id: null,
  returned_quantity: 1
})

const movementTypes = computed(() => [
  { label: t('gadgetStock.movementTypes.restock'), value: 'RESTOCK' },
  { label: t('gadgetStock.movementTypes.transfer'), value: 'TRANSFER' },
  { label: t('gadgetStock.movementTypes.delivery'), value: 'DELIVERY' },
  { label: t('gadgetStock.movementTypes.loan'), value: 'LOAN' },
  { label: t('gadgetStock.movementTypes.loan_return'), value: 'LOAN_RETURN' }
])

const movementTypeFilterOptions = computed(() => [
  { label: t('gadgetStock.allTypes'), value: null },
  ...movementTypes.value
])

const activeLoanOptions = computed(() => {
  return loans.value
    .filter(l => l.status !== 'RETURNED' && (l.remaining_quantity > 0 || (l.quantity - l.returned_quantity) > 0))
    .map(l => ({
      label: `#${l.id} - ${l.gadget_name || 'Gadget'} (Affidato a: ${l.assigned_to_name || 'Socio'}) - Residuo: ${l.remaining_quantity} pz`,
      value: l.id,
      loan: l
    }))
})

const selectedLoanInMovementForm = computed(() => {
  if (movementForm.value.movement_type !== 'LOAN_RETURN' || !movementForm.value.loan_id) return null
  return loans.value.find(l => l.id === movementForm.value.loan_id) || null
})

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
    const loanRemainingTotal = loans.value
      .filter(l => l.gadget_id === g.id && l.status !== 'RETURNED')
      .reduce((sum, l) => sum + (l.remaining_quantity || 0), 0)
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
      loan_remaining_total: loanRemainingTotal,
      is_not_for_sale: g.is_not_for_sale || false,
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

const selectedGadgetNotForSale = computed(() => {
  if (!movementForm.value.gadget_id) return false
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  return !!gadget?.is_not_for_sale
})

const totalStockPieces = computed(() => {
  return flattenedStocks.value.reduce((acc, curr) => acc + curr.total_stock, 0)
})

watch(() => movementForm.value.gadget_id, () => {
  if (movementForm.value.movement_type !== 'LOAN_RETURN') {
    movementForm.value.from_warehouse_id = null
    movementForm.value.to_warehouse_id = null
  }
})

watch(() => movementForm.value.movement_type, (newType) => {
  if (newType === 'RESTOCK') {
    movementForm.value.from_warehouse_id = null
  } else if (newType === 'DELIVERY' || newType === 'LOAN') {
    movementForm.value.to_warehouse_id = null
  } else if (newType === 'LOAN_RETURN') {
    movementForm.value.from_warehouse_id = null
    if (!movementForm.value.loan_id && activeLoanOptions.value.length > 0) {
      movementForm.value.loan_id = activeLoanOptions.value[0].value
    }
  }
})

watch(() => movementForm.value.loan_id, (newLoanId) => {
  if (movementForm.value.movement_type === 'LOAN_RETURN' && newLoanId) {
    const loan = loans.value.find(l => l.id === newLoanId)
    if (loan) {
      movementForm.value.gadget_id = loan.gadget_id
      movementForm.value.returned_quantity = loan.remaining_quantity
      movementForm.value.to_warehouse_id = loan.from_warehouse_id || (warehouses.value.find(w => w.is_active !== false)?.id || null)
    }
  }
})

const totalLoanedPieces = computed(() => {
  return loans.value
    .filter(l => l.status !== 'RETURNED')
    .reduce((sum, l) => sum + (l.remaining_quantity || 0), 0)
})

const activeLoansList = computed(() => {
  if (showOnlyActiveLoans.value) {
    return loans.value.filter(l => l.status !== 'RETURNED')
  }
  return loans.value
})

async function loadData() {
  loading.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const headers = { Authorization: `Bearer ${token}` }
    // Richieste eseguite in parallelo (Promise.all) invece che in sequenza:
    // la pagina è pronta in un solo round-trip "logico" e il backend (macchine
    // piccole) gestisce meno richieste a cascata.
    const [resGadgets, resWarehouses, resMovements, resLoans, resAssignees] = await Promise.all([
      fetch(API_URL + "/gadgets/", { headers }),
      fetch(API_URL + "/gadgets/warehouses", { headers }),
      fetch(API_URL + "/gadgets/movements", { headers }),
      fetch(API_URL + "/gadgets/loans?status=ALL", { headers }),
      fetch(API_URL + "/gadgets/loan-assignees", { headers })
    ])
    if (resGadgets.ok) gadgets.value = await resGadgets.json()
    if (resWarehouses.ok) warehouses.value = await resWarehouses.json()
    if (resMovements.ok) {
      const data = await resMovements.json()
      movements.value = data.map(m => ({
        ...m,
        performed_by_display: formatPerformedBy(m)
      }))
    }
    if (resLoans.ok) loans.value = await resLoans.json()
    if (resAssignees.ok) loanAssignees.value = await resAssignees.json()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.loadFailed'), life: 3000 })
  } finally {
    loading.value = false
  }
}

function openMovementModal(type = 'RESTOCK', loanId = null) {
  movementForm.value = {
    gadget_id: null,
    movement_type: type,
    from_warehouse_id: null,
    to_warehouse_id: null,
    quantity: 1,
    notes: '',
    assigned_to_user_id: null,
    assigned_to_name: '',
    expected_return_date: null,
    loan_id: loanId,
    returned_quantity: 1
  }

  if (type === 'LOAN_RETURN') {
    if (loanId) {
      const loan = loans.value.find(l => l.id === loanId)
      if (loan) {
        movementForm.value.gadget_id = loan.gadget_id
        movementForm.value.returned_quantity = loan.remaining_quantity
        movementForm.value.to_warehouse_id = loan.from_warehouse_id || (warehouses.value.find(w => w.is_active !== false)?.id || null)
      }
    } else if (activeLoanOptions.value.length > 0) {
      movementForm.value.loan_id = activeLoanOptions.value[0].value
      const loan = loans.value.find(l => l.id === activeLoanOptions.value[0].value)
      if (loan) {
        movementForm.value.gadget_id = loan.gadget_id
        movementForm.value.returned_quantity = loan.remaining_quantity
        movementForm.value.to_warehouse_id = loan.from_warehouse_id || (warehouses.value.find(w => w.is_active !== false)?.id || null)
      }
    }
  }

  showMovementDialog.value = true
}

async function submitMovement() {
  if (movementForm.value.movement_type === 'LOAN_RETURN') {
    if (!movementForm.value.loan_id) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Seleziona l'affidamento da riconsegnare", life: 3000 })
      return
    }
    const targetLoan = loans.value.find(l => l.id === movementForm.value.loan_id)
    if (!targetLoan) {
      toast.add({ severity: 'error', summary: t('common.error'), detail: "Affidamento non trovato", life: 3000 })
      return
    }
    const retQty = Number(movementForm.value.returned_quantity) || 0

    if (retQty <= 0) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Specifica la quantità da restituire (almeno 1 pz)", life: 3000 })
      return
    }
    if (retQty > targetLoan.remaining_quantity) {
      toast.add({ severity: 'error', summary: t('common.error'), detail: `La quantità da restituire supera il residuo in carico (${targetLoan.remaining_quantity} pz)`, life: 4000 })
      return
    }
    if (!movementForm.value.to_warehouse_id) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Seleziona il magazzino di rientro", life: 3000 })
      return
    }

    submitting.value = true
    try {
      const token = (await supabase.auth.getSession()).data.session?.access_token
      const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
      const res = await fetch(`${API_URL}/gadgets/loans/${movementForm.value.loan_id}/return`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          returned_quantity: retQty,
          to_warehouse_id: movementForm.value.to_warehouse_id,
          notes: movementForm.value.notes
        })
      })
      if (res.ok) {
        toast.add({ severity: 'success', summary: "Riconsegnato", detail: t('gadgetStock.returnSuccess'), life: 3000 })
        showMovementDialog.value = false
        await loadData()
      } else {
        const errDetail = await res.json()
        toast.add({ severity: 'error', summary: t('common.error'), detail: errDetail.detail || "Errore durante la riconsegna", life: 4000 })
      }
    } catch (err) {
      console.error(err)
      toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.connectionFailed'), life: 3000 })
    } finally {
      submitting.value = false
    }
    return
  }

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
  if (['DELIVERY', 'LOAN'].includes(movementForm.value.movement_type) && !movementForm.value.from_warehouse_id) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: t('gadgetStock.errors.selectSource'), life: 3000 })
    return
  }
  if (movementForm.value.movement_type === 'LOAN') {
    if (!movementForm.value.assigned_to_user_id && !movementForm.value.assigned_to_name?.trim()) {
      toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Seleziona o specifica a chi è affidato il materiale", life: 3000 })
      return
    }
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
    const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    
    if (movementForm.value.movement_type === 'LOAN') {
      const res = await fetch(API_URL + "/gadgets/loans", {
        method: 'POST',
        headers,
        body: JSON.stringify({
          gadget_id: movementForm.value.gadget_id,
          from_warehouse_id: movementForm.value.from_warehouse_id,
          quantity: movementForm.value.quantity,
          assigned_to_user_id: movementForm.value.assigned_to_user_id,
          assigned_to_name: movementForm.value.assigned_to_name,
          expected_return_date: movementForm.value.expected_return_date,
          notes: movementForm.value.notes
        })
      })
      if (res.ok) {
        toast.add({ severity: 'success', summary: t('gadgetStock.registered'), detail: t('gadgetStock.loanSuccess'), life: 3000 })
        showMovementDialog.value = false
        await loadData()
      } else {
        const errDetail = await res.json()
        toast.add({ severity: 'error', summary: t('common.error'), detail: errDetail.detail || t('gadgetStock.errors.movementFailed'), life: 4000 })
      }
    } else {
      const res = await fetch(API_URL + "/gadgets/movements", {
        method: 'POST',
        headers,
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
        await loadData()
      } else {
        const errDetail = await res.json()
        toast.add({ severity: 'error', summary: t('common.error'), detail: errDetail.detail || t('gadgetStock.errors.movementFailed'), life: 4000 })
      }
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.connectionFailed'), life: 3000 })
  } finally {
    submitting.value = false
  }
}

function openReturnModal(loan) {
  selectedLoan.value = loan
  returnForm.value = {
    returned_quantity: loan.remaining_quantity,
    to_warehouse_id: loan.from_warehouse_id || (warehouses.value.find(w => w.is_active !== false)?.id || null),
    notes: ''
  }
  showReturnDialog.value = true
}

async function submitReturn() {
  if (!selectedLoan.value) return
  const retQty = Number(returnForm.value.returned_quantity) || 0
  if (retQty <= 0) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Specifica la quantità da restituire (almeno 1 pz)", life: 3000 })
    return
  }
  if (!returnForm.value.to_warehouse_id) {
    toast.add({ severity: 'warn', summary: t('common.warning'), detail: "Seleziona il magazzino di rientro", life: 3000 })
    return
  }
  if (retQty > selectedLoan.value.remaining_quantity) {
    toast.add({ severity: 'error', summary: t('common.error'), detail: `La quantità supera il residuo in carico (${selectedLoan.value.remaining_quantity} pz)`, life: 4000 })
    return
  }

  returningSubmitting.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }
    const res = await fetch(`${API_URL}/gadgets/loans/${selectedLoan.value.id}/return`, {
      method: 'POST',
      headers,
      body: JSON.stringify(returnForm.value)
    })
    if (res.ok) {
      toast.add({ severity: 'success', summary: "Riconsegnato", detail: t('gadgetStock.returnSuccess'), life: 3000 })
      showReturnDialog.value = false
      await loadData()
    } else {
      const err = await res.json()
      toast.add({ severity: 'error', summary: t('common.error'), detail: err.detail || "Errore durante la riconsegna", life: 4000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('gadgetStock.errors.connectionFailed'), life: 3000 })
  } finally {
    returningSubmitting.value = false
  }
}

function getMovementTypeBadgeClass(type) {
  switch (type) {
    case 'RESTOCK': return 'bg-green-600'
    case 'TRANSFER': return 'bg-blue-600'
    case 'DELIVERY': return 'bg-orange-500'
    case 'LOAN': return 'bg-purple-600'
    case 'LOAN_RETURN': return 'bg-teal-600'
    default: return 'bg-gray-500'
  }
}

function getMovementTypeLabel(type) {
  switch (type) {
    case 'RESTOCK': return t('gadgetStock.movementTypes.restock')
    case 'TRANSFER': return t('gadgetStock.movementTypes.transfer')
    case 'DELIVERY': return t('gadgetStock.movementTypes.delivery')
    case 'LOAN': return t('gadgetStock.movementTypes.loan')
    case 'LOAN_RETURN': return t('gadgetStock.movementTypes.loan_return')
    default: return type
  }
}

function formatPerformedBy(m) {
  if (!m) return '-'
  if (m.performer) {
    const lastName = m.performer.last_name ? m.performer.last_name.trim() : ''
    const id = m.performer.id || m.performed_by
    if (lastName) {
      return `${lastName} (#${id})`
    }
    const firstName = m.performer.first_name ? m.performer.first_name.trim() : ''
    if (firstName) {
      return `${firstName} (#${id})`
    }
    return `(#${id})`
  }
  if (m.performed_by) {
    return `(${m.performed_by})`
  }
  return '-'
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
            <div class="text-3xl font-bold text-purple-600">{{ totalLoanedPieces }}</div>
            <div class="text-sm text-secondary uppercase font-semibold mt-1">{{ t('gadgetStock.activeLoans') }}</div>
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
                <img v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Gadget" loading="lazy" decoding="async" class="w-full h-full object-fit-cover" />
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
          <Column v-if="isAdminOrSecretary" field="is_not_for_sale" :header="t('gadgetStock.notForSale')" sortable>
            <template #body="slotProps">
              <span v-if="slotProps.data.is_not_for_sale" class="badge border-round px-2 py-1 text-xs bg-orange-100 text-orange-800 font-semibold">
                <i class="pi pi-ban text-xs mr-1"></i>{{ t('gadgetStock.notForSaleShort') }}
              </span>
              <span v-else class="text-xs text-400">-</span>
            </template>
          </Column>
          <Column field="total_stock" :header="t('gadgetStock.totalStock')" sortable class="bg-surface-50">
            <template #body="slotProps">
              <div class="flex align-items-center gap-2">
                <span :class="['font-bold', slotProps.data.total_stock < 1 ? 'text-red-500' : 'text-primary']">{{ slotProps.data.total_stock }} {{ t('gadgetStock.pcs') }}</span>
                <span v-if="slotProps.data.loan_remaining_total > 0" class="badge border-round px-2 py-1 text-xs bg-purple-100 text-purple-800 font-bold white-space-nowrap" :title="'Affidati attivi: ' + slotProps.data.loan_remaining_total + ' pz'">🤝 {{ slotProps.data.loan_remaining_total }} {{ t('gadgetStock.pcs') }}</span>
              </div>
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

    <!-- Loans Section -->
    <div class="col-12 mb-5">
      <div class="card p-4 shadow-2 border-round surface-card">
        <div class="flex flex-column sm:flex-row justify-content-between align-items-start sm:align-items-center gap-3 mb-4">
          <div>
            <h3 class="text-xl font-bold m-0 text-900 flex align-items-center gap-2">
              <i class="pi pi-briefcase text-purple-600"></i>
              {{ t('gadgetStock.loansTitle') }}
              <span class="badge border-round px-2 py-1 text-xs bg-purple-100 text-purple-800 font-bold ml-1">
                {{ activeLoansList.length }}
              </span>
            </h3>
            <p class="text-secondary text-sm m-0 mt-1">{{ t('gadgetStock.loansSubtitle') }}</p>
          </div>
          <div class="flex flex-wrap align-items-center gap-2">
            <Button 
              :label="showOnlyActiveLoans ? 'Solo in corso' : 'Tutti'" 
              :icon="showOnlyActiveLoans ? 'pi pi-filter' : 'pi pi-list'" 
              severity="secondary" 
              outlined 
              size="small" 
              @click="showOnlyActiveLoans = !showOnlyActiveLoans" 
            />
            <Button 
              :label="t('gadgetStock.newLoan')" 
              icon="pi pi-plus" 
              severity="help" 
              outlined 
              size="small" 
              @click="openMovementModal('LOAN')" 
            />
            <Button 
              :label="t('gadgetStock.quickReturn')" 
              icon="pi pi-replay" 
              severity="success" 
              outlined 
              size="small" 
              @click="openMovementModal('LOAN_RETURN')" 
            />
          </div>
        </div>

        <DataTable :value="activeLoansList" :loading="loading" paginator :rows="5" responsiveLayout="scroll">
          <template #empty>
            <div class="text-center py-4">
              <i class="pi pi-check-circle text-3xl text-green-500 mb-2"></i>
              <p class="m-0 text-color-secondary">Nessun oggetto attualmente in affidamento temporaneo</p>
            </div>
          </template>
          <Column :header="t('gadgetStock.photo')" class="w-5rem text-center">
            <template #body="slotProps">
              <div class="flex align-items-center justify-content-center m-auto border-1 border-light border-round overflow-hidden" style="width: 40px; height: 50px; background-color: var(--code-bg);">
                <img v-if="slotProps.data.gadget_image" :src="getImageUrl(slotProps.data.gadget_image)" alt="Gadget" loading="lazy" decoding="async" class="w-full h-full object-fit-cover" />
                <i v-else class="pi pi-image text-color-secondary text-base"></i>
              </div>
            </template>
          </Column>
          <Column field="gadget_name" :header="t('gadgetStock.gadget')" sortable class="font-bold">
            <template #body="slotProps">
              <div>{{ slotProps.data.gadget_name }}</div>
              <small v-if="slotProps.data.gadget_sku" class="text-color-secondary font-normal">[SKU: {{ slotProps.data.gadget_sku }}]</small>
            </template>
          </Column>
          <Column field="assigned_to_name" :header="t('gadgetStock.assignee')" sortable class="font-semibold">
            <template #body="slotProps">
              <div class="flex align-items-center gap-2">
                <i class="pi pi-user text-purple-600 text-sm"></i>
                <span>{{ slotProps.data.assigned_to_name }}</span>
              </div>
            </template>
          </Column>
          <Column field="from_warehouse_name" header="Magazzino Origine" sortable>
            <template #body="slotProps">
              <span class="text-sm text-color-secondary">{{ slotProps.data.from_warehouse_name || '-' }}</span>
            </template>
          </Column>
          <Column field="remaining_quantity" header="In Carico" sortable>
            <template #body="slotProps">
              <span class="font-bold text-purple-700 text-base">{{ slotProps.data.remaining_quantity }} pz</span>
              <small v-if="slotProps.data.returned_quantity > 0" class="block text-xxs text-color-secondary">
                (Iniziali: {{ slotProps.data.quantity }})
              </small>
            </template>
          </Column>
          <Column field="status" :header="t('gadgetStock.statusLoan')" sortable>
            <template #body="slotProps">
              <span v-if="slotProps.data.status === 'RETURNED'" class="badge bg-green-100 text-green-800 text-xs px-2 py-1 border-round font-semibold">
                <i class="pi pi-check text-xs mr-1"></i> {{ t('gadgetStock.statusReturned') }}
              </span>
              <span v-else-if="slotProps.data.status === 'PARTIAL'" class="badge bg-amber-100 text-amber-800 text-xs px-2 py-1 border-round font-semibold">
                <i class="pi pi-clock text-xs mr-1"></i> {{ t('gadgetStock.statusPartial') }}
              </span>
              <span v-else class="badge bg-purple-100 text-purple-800 text-xs px-2 py-1 border-round font-semibold">
                <i class="pi pi-user text-xs mr-1"></i> {{ t('gadgetStock.statusActive') }}
              </span>
            </template>
          </Column>
          <Column field="loan_date" header="Data Consegna" sortable>
            <template #body="slotProps">
              <span class="text-sm">{{ formatDate(slotProps.data.loan_date) }}</span>
            </template>
          </Column>
          <Column field="expected_return_date" header="Rientro Previsto" sortable>
            <template #body="slotProps">
              <div v-if="slotProps.data.status === 'RETURNED'" class="text-sm text-green-600 font-semibold">
                <i class="pi pi-check text-xs mr-1"></i> Riconsegnato
              </div>
              <div v-else-if="slotProps.data.expected_return_date" class="flex align-items-center gap-1">
                <span class="text-sm">{{ slotProps.data.expected_return_date }}</span>
                <span v-if="slotProps.data.is_overdue" class="badge bg-red-500 text-white font-bold text-xxs px-1 py-0.5 border-round">
                  {{ t('gadgetStock.overdue') }}
                </span>
              </div>
              <span v-else class="text-sm text-color-secondary">-</span>
            </template>
          </Column>
          <Column field="notes" :header="t('gadgetStock.notes')">
            <template #body="slotProps">
              <span class="text-sm text-color-secondary">{{ slotProps.data.notes || '-' }}</span>
            </template>
          </Column>
          <Column header="Azioni" class="text-right" style="min-width: 120px">
            <template #body="slotProps">
              <Button 
                v-if="slotProps.data.status !== 'RETURNED'" 
                :label="t('gadgetStock.returnBtn')" 
                icon="pi pi-replay" 
                severity="success" 
                size="small" 
                @click="openReturnModal(slotProps.data)" 
              />
              <span v-else class="badge bg-green-100 text-green-800 text-xs px-2 py-1 border-round font-semibold">
                Completato
              </span>
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
                <img v-if="slotProps.data.image_path" :src="getImageUrl(slotProps.data.image_path)" alt="Movimento" loading="lazy" decoding="async" class="w-full h-full object-fit-cover" />
                <i v-else class="pi pi-image text-color-secondary text-lg"></i>
              </div>
            </template>
          </Column>
          <Column field="timestamp" :header="t('gadgetStock.dateTime')" sortable>
            <template #body="slotProps">{{ formatDate(slotProps.data.timestamp) }}</template>
          </Column>
          <Column field="movement_type" :header="t('gadgetStock.type')" sortable filter filterField="movement_type" :showFilterMenu="false" :showClearButton="true">
            <template #body="slotProps">
              <span :class="['badge border-round px-2 py-1 text-xs text-white font-bold', getMovementTypeBadgeClass(slotProps.data.movement_type)]">{{ getMovementTypeLabel(slotProps.data.movement_type) }}</span>
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
              <span class="text-sm" v-if="slotProps.data.movement_type === 'LOAN'">
                <span class="font-semibold">{{ slotProps.data.from_warehouse ? slotProps.data.from_warehouse.name : 'Magazzino' }}</span>
                <i class="pi pi-arrow-right text-xs mx-2 text-purple-600"></i>
                <span class="text-purple-700 font-semibold">{{ t('gadgetStock.assignedLoan') }}</span>
              </span>
              <span class="text-sm" v-else-if="slotProps.data.movement_type === 'LOAN_RETURN'">
                <span class="text-purple-700 font-semibold">{{ t('gadgetStock.assignedLoan') }}</span>
                <i class="pi pi-arrow-right text-xs mx-2 text-teal-600"></i>
                <span class="font-semibold text-teal-700">{{ slotProps.data.to_warehouse ? slotProps.data.to_warehouse.name : 'Magazzino' }}</span>
              </span>
              <span class="text-sm" v-else>
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
          <Column field="performed_by_display" :header="t('gadgetStock.performedby')" sortable filter filterField="performed_by_display" :showFilterMenu="false" :showClearButton="true">
            <template #body="slotProps">
              <span>{{ slotProps.data.performed_by_display ? slotProps.data.performed_by_display : '-' }}</span>
            </template>
            <template #filter="{ filterModel, filterCallback }">
              <InputText v-model="filterModel.value" @input="filterCallback()" :placeholder="t('gadgetStock.searchPerformedBy')" class="w-full" />
            </template>
          </Column>
        </DataTable>
      </div>
    </div>
  </div>

  <!-- Movement Dialog -->
  <Dialog 
    v-model:visible="showMovementDialog" 
    :header="movementForm.movement_type === 'LOAN_RETURN' ? t('gadgetStock.returnDialogTitle') : t('gadgetStock.movementDialogTitle')" 
    :modal="true" 
    :style="{ width: '520px' }"
  >
    <div class="flex flex-column gap-4 py-2 text-left">
      <div class="flex flex-column gap-2">
        <label for="m_type" class="font-semibold text-sm">{{ t('gadgetStock.form.movementType') }} *</label>
        <Select inputId="m_type" v-model="movementForm.movement_type" :options="movementTypes" optionLabel="label" optionValue="value" class="w-full" />
      </div>

      <!-- IF MOVEMENT IS LOAN RETURN -->
      <template v-if="movementForm.movement_type === 'LOAN_RETURN'">
        <div class="flex flex-column gap-2">
          <label for="m_loan_select" class="font-semibold text-sm">{{ t('gadgetStock.selectLoan') }} *</label>
          <Select 
            inputId="m_loan_select" 
            v-model="movementForm.loan_id" 
            :options="activeLoanOptions" 
            optionLabel="label" 
            optionValue="value" 
            :placeholder="t('gadgetStock.selectLoan')" 
            filter 
            class="w-full" 
          />
        </div>

        <div v-if="!activeLoanOptions.length" class="p-3 bg-amber-50 border-round text-amber-900 text-sm">
          <i class="pi pi-info-circle mr-1"></i> Nessun materiale attualmente in affidamento temporaneo da riconsegnare.
        </div>

        <div v-if="selectedLoanInMovementForm" class="p-3 border-round border-1 border-light" style="background-color: var(--code-bg);">
          <div class="flex align-items-center gap-3 mb-2">
            <div class="border-round border-1 border-light overflow-hidden flex align-items-center justify-content-center" style="width: 40px; height: 50px; background-color: var(--bg); flex-shrink: 0;">
              <img v-if="selectedLoanInMovementForm.gadget_image" :src="getImageUrl(selectedLoanInMovementForm.gadget_image)" alt="Gadget" class="w-full h-full object-fit-cover" />
              <i v-else class="pi pi-image text-color-secondary text-base"></i>
            </div>
            <div>
              <div class="font-bold text-base text-900">{{ selectedLoanInMovementForm.gadget_name }}</div>
              <div class="text-xs text-secondary" v-if="selectedLoanInMovementForm.gadget_sku">[SKU: {{ selectedLoanInMovementForm.gadget_sku }}]</div>
            </div>
          </div>
          <div class="text-sm text-color-secondary mb-1">
            Affidato a: <strong class="text-900">{{ selectedLoanInMovementForm.assigned_to_name }}</strong>
          </div>
          <div class="flex flex-wrap gap-3 text-xs font-semibold uppercase text-purple-700">
            <span>Residuo in carico: {{ selectedLoanInMovementForm.remaining_quantity }} pz</span>
            <span v-if="selectedLoanInMovementForm.from_warehouse_name">Origine: {{ selectedLoanInMovementForm.from_warehouse_name }}</span>
          </div>
        </div>

        <template v-if="selectedLoanInMovementForm">
          <div class="flex flex-column gap-2">
            <label for="m_ret_qty" class="font-semibold text-sm">{{ t('gadgetStock.returnedQty') }} *</label>
            <InputNumber 
              inputId="m_ret_qty" 
              v-model="movementForm.returned_quantity" 
              :min="1" 
              :max="selectedLoanInMovementForm.remaining_quantity" 
              class="w-full" 
              showButtons 
            />
            <small class="text-color-secondary text-xs">Pezzi da restituire al magazzino (residuo: {{ selectedLoanInMovementForm.remaining_quantity }} pz)</small>
          </div>

          <div class="flex flex-column gap-2">
            <label for="m_ret_wh" class="font-semibold text-sm">{{ t('gadgetStock.returnWarehouse') }} *</label>
            <Select 
              inputId="m_ret_wh" 
              v-model="movementForm.to_warehouse_id" 
              :options="warehouses.filter(w => w.is_active !== false)" 
              optionLabel="name" 
              optionValue="id" 
              placeholder="Seleziona magazzino..." 
              class="w-full" 
            />
          </div>
        </template>
      </template>

      <!-- IF MOVEMENT IS RESTOCK, TRANSFER, DELIVERY, LOAN -->
      <template v-else>
        <div class="flex flex-column gap-2">
          <label for="m_gadget" class="font-semibold text-sm">{{ t('gadgetStock.form.gadget') }} *</label>
          <Select inputId="m_gadget" v-model="movementForm.gadget_id" :options="gadgetOptions" optionLabel="label" optionValue="value" :placeholder="t('gadgetStock.form.selectGadget')" filter class="w-full" />
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
            <span v-if="selectedGadgetNotForSale" class="badge border-round px-2 py-1 text-xs bg-orange-100 text-orange-800 font-semibold align-self-start">
              <i class="pi pi-ban text-xs mr-1"></i>{{ t('gadgetStock.notForSaleShort') }}
            </span>
          </div>
        </div>
        <div class="flex flex-column gap-2" v-if="['TRANSFER', 'DELIVERY', 'LOAN'].includes(movementForm.movement_type)">
          <label for="m_from" class="font-semibold text-sm">{{ t('gadgetStock.form.sourceWarehouse') }} *</label>
          <Select inputId="m_from" v-model="movementForm.from_warehouse_id" :options="fromWarehouseOptions.filter(opt => opt.value !== movementForm.to_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.gadget_id ? t('gadgetStock.form.selectSource') : 'Seleziona prima un gadget'" :disabled="!movementForm.gadget_id" class="w-full" />
        </div>
        <div class="flex flex-column gap-2" v-if="['RESTOCK', 'TRANSFER'].includes(movementForm.movement_type)">
          <label for="m_to" class="font-semibold text-sm">{{ t('gadgetStock.form.destinationWarehouse') }} *</label>
          <Select inputId="m_to" v-model="movementForm.to_warehouse_id" :options="toWarehouseOptions.filter(opt => opt.value !== movementForm.from_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.gadget_id ? t('gadgetStock.form.selectDestination') : 'Seleziona prima un gadget'" :disabled="!movementForm.gadget_id" class="w-full" />
        </div>

        <!-- Campi specifici per AFFIDAMENTO (LOAN) -->
        <template v-if="movementForm.movement_type === 'LOAN'">
          <div class="flex flex-column gap-2">
            <label for="m_assignee_user" class="font-semibold text-sm">{{ t('gadgetStock.assignee') }} (Socio registrato)</label>
            <Select 
              inputId="m_assignee_user" 
              v-model="movementForm.assigned_to_user_id" 
              :options="loanAssignees" 
              optionLabel="display" 
              optionValue="id" 
              :placeholder="t('gadgetStock.selectAssignee')" 
              showClear 
              filter 
              class="w-full" 
            />
          </div>
          <div class="flex flex-column gap-2">
            <label for="m_assignee_name" class="font-semibold text-sm">{{ t('gadgetStock.customAssignee') }}</label>
            <InputText 
              id="m_assignee_name" 
              v-model="movementForm.assigned_to_name" 
              placeholder="es. Mario Rossi (Volontario)" 
              :disabled="!!movementForm.assigned_to_user_id" 
              class="w-full" 
            />
          </div>
          <div class="flex flex-column gap-2">
            <label for="m_expected_date" class="font-semibold text-sm">{{ t('gadgetStock.expectedReturnDate') }}</label>
            <input 
              type="date" 
              id="m_expected_date" 
              v-model="movementForm.expected_return_date" 
              class="p-inputtext p-component w-full" 
            />
          </div>
        </template>

        <div class="flex flex-column gap-2">
          <label for="m_qty" class="font-semibold text-sm">{{ t('gadgetStock.form.quantity') }} *</label>
          <InputNumber inputId="m_qty" v-model="movementForm.quantity" :min="1" :placeholder="t('gadgetStock.form.quantityPlaceholder')" class="w-full" showButtons />
        </div>
      </template>

      <div class="flex flex-column gap-2">
        <label for="m_notes" class="font-semibold text-sm">{{ t('gadgetStock.form.notes') }}</label>
        <InputText id="m_notes" v-model="movementForm.notes" :placeholder="t('gadgetStock.form.notesPlaceholder')" class="w-full" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="showMovementDialog = false" />
      <Button :label="movementForm.movement_type === 'LOAN_RETURN' ? 'Conferma Riconsegna' : t('gadgetStock.form.register')" severity="success" :loading="submitting" @click="submitMovement" />
    </template>
  </Dialog>

  <!-- Return Dialog -->
  <Dialog v-model:visible="showReturnDialog" :header="t('gadgetStock.returnDialogTitle')" :modal="true" :style="{ width: '480px' }">
    <div v-if="selectedLoan" class="flex flex-column gap-3 py-2 text-left">
      <div class="p-3 border-round border-1 border-light" style="background-color: var(--code-bg);">
        <div class="font-bold text-base text-900 mb-1">{{ selectedLoan.gadget_name }}</div>
        <div class="text-sm text-color-secondary mb-2">
          Affidato a: <strong class="text-900">{{ selectedLoan.assigned_to_name }}</strong>
        </div>
        <div class="flex gap-4 text-xs font-semibold uppercase text-purple-700">
          <span>Residuo in carico: {{ selectedLoan.remaining_quantity }} pz</span>
          <span v-if="selectedLoan.from_warehouse_name">Partito da: {{ selectedLoan.from_warehouse_name }}</span>
        </div>
      </div>

      <div class="flex flex-column gap-2">
        <label for="ret_qty" class="font-semibold text-sm">{{ t('gadgetStock.returnedQty') }} *</label>
        <InputNumber 
          inputId="ret_qty" 
          v-model="returnForm.returned_quantity" 
          :min="1" 
          :max="selectedLoan.remaining_quantity" 
          class="w-full" 
          showButtons 
        />
        <small class="text-color-secondary text-xs">Pezzi da restituire al magazzino (residuo in carico: {{ selectedLoan.remaining_quantity }} pz)</small>
      </div>

      <div class="flex flex-column gap-2">
        <label for="ret_wh" class="font-semibold text-sm">{{ t('gadgetStock.returnWarehouse') }} *</label>
        <Select 
          inputId="ret_wh" 
          v-model="returnForm.to_warehouse_id" 
          :options="warehouses.filter(w => w.is_active !== false)" 
          optionLabel="name" 
          optionValue="id" 
          placeholder="Seleziona magazzino..." 
          class="w-full" 
        />
      </div>

      <div class="flex flex-column gap-2">
        <label for="ret_notes" class="font-semibold text-sm">{{ t('gadgetStock.form.notes') }}</label>
        <InputText id="ret_notes" v-model="returnForm.notes" placeholder="Note sulla riconsegna..." class="w-full" />
      </div>
    </div>
    <template #footer>
      <Button :label="t('common.cancel')" severity="secondary" outlined @click="showReturnDialog = false" />
      <Button label="Conferma Riconsegna" severity="success" icon="pi pi-check" :loading="returningSubmitting" @click="submitReturn" />
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
