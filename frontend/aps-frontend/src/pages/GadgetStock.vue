<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useToast } from 'primevue/usetoast'

// PrimeVue Components
import Button from 'primevue/button'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Dialog from 'primevue/dialog'
import Card from 'primevue/card'

const { getAccessTokenSilently } = useAuth0()
const toast = useToast()

// State
const gadgets = ref([])
const warehouses = ref([])
const movements = ref([])
const loading = ref(false)
const showMovementDialog = ref(false)
const submitting = ref(false)

// Form state
const movementForm = ref({
  gadget_id: null,
  variant_id: null,
  movement_type: 'RESTOCK', // RESTOCK, TRANSFER, DELIVERY
  from_warehouse_id: null,
  to_warehouse_id: null,
  quantity: 1,
  notes: ''
})

// Options mapping
const movementTypes = [
  { label: 'Rifornimento (RESTOCK)', value: 'RESTOCK' },
  { label: 'Trasferimento (TRANSFER)', value: 'TRANSFER' },
  { label: 'Consegna a socio (DELIVERY)', value: 'DELIVERY' }
]

// Computed properties
const variantsOptions = computed(() => {
  if (!movementForm.value.gadget_id) return []
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget) return []
  return gadget.variants.map(v => ({
    label: `${v.size || ''} ${v.color || ''} ${v.model || ''} [SKU: ${v.sku || v.id}] (Stock: ${v.stock_quantity})`,
    value: v.id,
    sku: v.sku,
    stocks: v.stocks
  }))
})

const fromWarehouseOptions = computed(() => {
  if (!movementForm.value.variant_id) return []
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget) return []
  const variant = gadget.variants.find(v => v.id === movementForm.value.variant_id)
  if (!variant) return []
  
  const options = []
  variant.stocks.forEach(stock => {
    if (stock.quantity > 0) {
      const wh = warehouses.value.find(w => w.id === stock.warehouse_id)
      if (wh) {
        options.push({
          label: `${wh.name} (${stock.quantity} pz)`,
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
  if (!movementForm.value.variant_id) {
    return warehouses.value.map(w => ({
      label: `${w.name} (0 pz)`,
      value: w.id,
      quantity: 0
    }))
  }
  
  const gadget = gadgets.value.find(g => g.id === movementForm.value.gadget_id)
  if (!gadget) return []
  const variant = gadget.variants.find(v => v.id === movementForm.value.variant_id)
  if (!variant) return []

  return warehouses.value.map(w => {
    const stock = variant.stocks.find(s => s.warehouse_id === w.id)
    const quantity = stock ? stock.quantity : 0
    return {
      label: `${w.name} (${quantity} pz)`,
      value: w.id,
      quantity: quantity
    }
  })
})

// Flattened variants for current stock table
const flattenedStocks = computed(() => {
  const list = []
  gadgets.value.forEach(g => {
    g.variants.forEach(v => {
      // Find stock in each warehouse
      const stockMap = {}
      warehouses.value.forEach(w => {
        const found = v.stocks.find(s => s.warehouse_id === w.id)
        stockMap[w.code] = found ? found.quantity : 0
      })
      list.push({
        id: v.id,
        gadget_name: g.name,
        category: g.category,
        sku: v.sku,
        size: v.size,
        color: v.color,
        model: v.model,
        total_stock: v.stock_quantity,
        ...stockMap
      })
    })
  })
  return list
})

const totalStockPieces = computed(() => {
  return flattenedStocks.value.reduce((acc, curr) => acc + curr.total_stock, 0)
})

// Watchers
watch(() => movementForm.value.gadget_id, () => {
  movementForm.value.variant_id = null
})

watch(() => movementForm.value.variant_id, () => {
  movementForm.value.from_warehouse_id = null
  movementForm.value.to_warehouse_id = null
})

watch(() => movementForm.value.movement_type, (newType) => {
  // Clear fields depending on movement type
  if (newType === 'RESTOCK') {
    movementForm.value.from_warehouse_id = null
  } else if (newType === 'DELIVERY') {
    movementForm.value.to_warehouse_id = null
  }
})

// Functions
async function loadData() {
  loading.value = true
  try {
    const token = await getAccessTokenSilently()
    const headers = { Authorization: `Bearer ${token}` }
    
    // Fetch gadgets
    const resGadgets = await fetch("http://localhost:8000/gadgets/", { headers })
    if (resGadgets.ok) gadgets.value = await resGadgets.json()

    // Fetch warehouses
    const resWarehouses = await fetch("http://localhost:8000/gadgets/warehouses", { headers })
    if (resWarehouses.ok) warehouses.value = await resWarehouses.json()

    // Fetch movements
    const resMovements = await fetch("http://localhost:8000/gadgets/movements", { headers })
    if (resMovements.ok) movements.value = await resMovements.json()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore nel caricamento dei dati', life: 3000 })
  } finally {
    loading.value = false
  }
}

function openMovementModal() {
  movementForm.value = {
    gadget_id: null,
    variant_id: null,
    movement_type: 'RESTOCK',
    from_warehouse_id: null,
    to_warehouse_id: null,
    quantity: 1,
    notes: ''
  }
  showMovementDialog.value = true
}

async function submitMovement() {
  // Client validation
  if (!movementForm.value.variant_id || !movementForm.value.quantity) {
    toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Compila tutti i campi obbligatori', life: 3000 })
    return
  }

  if (movementForm.value.movement_type === 'TRANSFER') {
    if (!movementForm.value.from_warehouse_id || !movementForm.value.to_warehouse_id) {
      toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Seleziona sia il magazzino di origine che di destinazione', life: 3000 })
      return
    }
    if (movementForm.value.from_warehouse_id === movementForm.value.to_warehouse_id) {
      toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Il magazzino di origine e destinazione devono essere differenti', life: 4000 })
      return
    }
  }
  if (movementForm.value.movement_type === 'RESTOCK' && !movementForm.value.to_warehouse_id) {
    toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Seleziona il magazzino di destinazione', life: 3000 })
    return
  }
  if (movementForm.value.movement_type === 'DELIVERY' && !movementForm.value.from_warehouse_id) {
    toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Seleziona il magazzino di origine', life: 3000 })
    return
  }

  // Validate stock level for Transfer or Delivery
  if (movementForm.value.movement_type !== 'RESTOCK') {
    const selectedVar = variantsOptions.value.find(v => v.value === movementForm.value.variant_id)
    const sourceStock = selectedVar?.stocks?.find(s => s.warehouse_id === movementForm.value.from_warehouse_id)?.quantity || 0
    if (sourceStock < movementForm.value.quantity) {
      toast.add({ severity: 'error', summary: 'Stock Insufficiente', detail: `Il magazzino selezionato ha solo ${sourceStock} unità di questa variante`, life: 4000 })
      return
    }
  }

  submitting.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch("http://localhost:8000/gadgets/movements", {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        variant_id: movementForm.value.variant_id,
        from_warehouse_id: movementForm.value.from_warehouse_id,
        to_warehouse_id: movementForm.value.to_warehouse_id,
        quantity: movementForm.value.quantity,
        movement_type: movementForm.value.movement_type,
        notes: movementForm.value.notes
      })
    })

    if (res.ok) {
      toast.add({ severity: 'success', summary: 'Registrato', detail: 'Movimento di magazzino registrato con successo', life: 3000 })
      showMovementDialog.value = false
      loadData()
    } else {
      const errDetail = await res.json()
      toast.add({ severity: 'error', summary: 'Errore', detail: errDetail.detail || 'Impossibile registrare il movimento', life: 4000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore di connessione', life: 3000 })
  } finally {
    submitting.value = false
  }
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('it-IT')
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="stock-container py-5 px-3">
    <!-- Header -->
    <div class="flex justify-content-between align-items-center mb-5">
      <div>
        <h2 class="font-bold text-3xl mb-1 text-900">Gestione Magazzino</h2>
        <p class="text-secondary text-sm m-0">Movimentazione dei gadget, tracciamento stock e storico delle operazioni</p>
      </div>
      <Button label="Registra Movimento" icon="pi pi-directions" severity="primary" @click="openMovementModal" />
    </div>

    <!-- KPIs -->
    <div class="flex flex-wrap gap-4 justify-content-between mb-5">
      <div class="flex-1 min-w-12rem">
        <Card class="shadow-1">
          <template #content>
            <div class="text-center">
              <div class="text-3xl font-bold text-primary">{{ totalStockPieces }}</div>
              <div class="text-sm text-secondary uppercase font-semibold mt-1">Pezzi Totali Stock</div>
            </div>
          </template>
        </Card>
      </div>
      <div class="flex-1 min-w-12rem">
        <Card class="shadow-1">
          <template #content>
            <div class="text-center">
              <div class="text-3xl font-bold text-cyan-600">{{ movements.length }}</div>
              <div class="text-sm text-secondary uppercase font-semibold mt-1">Movimenti Registrati</div>
            </div>
          </template>
        </Card>
      </div>
      <div class="flex-1 min-w-12rem">
        <Card class="shadow-1">
          <template #content>
            <div class="text-center">
              <div class="text-3xl font-bold text-orange-500">{{ warehouses.length }}</div>
              <div class="text-sm text-secondary uppercase font-semibold mt-1">Magazzini Attivi</div>
            </div>
          </template>
        </Card>
      </div>
    </div>

    <!-- Main Content Tabs/Grid -->
    <div class="grid">
      <!-- Giacenze per Variante -->
      <div class="col-12 mb-5">
        <div class="card p-4 shadow-2 border-round surface-card">
          <h3 class="text-xl font-bold mb-4 text-900">Giacenze per Variante</h3>
          <DataTable :value="flattenedStocks" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
            <template #empty>
              <div class="text-center py-4">
                <i class="pi pi-info-circle text-3xl text-400 mb-2"></i>
                <p class="m-0 text-color-secondary">Nessun gadget o variante caricata nel database.</p>
              </div>
            </template>
            <Column field="gadget_name" header="Gadget" sortable class="font-bold"></Column>
            <Column field="category" header="Categoria" sortable>
              <template #body="slotProps">
                <span class="badge border-round px-2 py-1 text-xs bg-cyan-100 text-cyan-800">
                  {{ slotProps.data.category }}
                </span>
              </template>
            </Column>
            <Column field="sku" header="SKU" sortable></Column>
            <Column header="Dettagli Variante">
              <template #body="slotProps">
                <span class="text-sm">
                  {{ slotProps.data.size ? 'Taglia: ' + slotProps.data.size : '' }}
                  {{ slotProps.data.color ? '| Colore: ' + slotProps.data.color : '' }}
                  {{ slotProps.data.model ? '| Modello: ' + slotProps.data.model : '' }}
                </span>
              </template>
            </Column>
            
            <Column field="total_stock" header="Totale Giacenza" sortable class="bg-surface-50">
              <template #body="slotProps">
                <span :class="['font-bold', slotProps.data.total_stock < 1 ? 'text-red-500' : 'text-primary']">
                  {{ slotProps.data.total_stock }} pz
                </span>
              </template>
            </Column>
            <!-- Dynamic Warehouse Columns -->
            <Column v-for="wh in warehouses" :key="wh.id" :field="wh.code" :header="wh.name" sortable>
              <template #body="slotProps">
                <span :class="['font-bold', slotProps.data[wh.code] > 0 ? 'text-green-600' : 'text-400']">
                  {{ slotProps.data[wh.code] }} pz
                </span>
              </template>
            </Column>

          </DataTable>
        </div>
      </div>

      <!-- Storico Movimenti -->
      <div class="col-12">
        <div class="card p-4 shadow-2 border-round surface-card">
          <h3 class="text-xl font-bold mb-4 text-900">Storico Movimenti</h3>
          <DataTable :value="movements" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
            <template #empty>
              <div class="text-center py-4">
                <i class="pi pi-history text-3xl text-400 mb-2"></i>
                <p class="m-0 text-color-secondary">Nessun movimento registrato.</p>
              </div>
            </template>
            <Column field="timestamp" header="Data e Ora" sortable>
              <template #body="slotProps">
                {{ formatDate(slotProps.data.timestamp) }}
              </template>
            </Column>
            <Column field="movement_type" header="Tipo" sortable>
              <template #body="slotProps">
                <span :class="['badge border-round px-2 py-1 text-xs text-white font-bold', 
                  slotProps.data.movement_type === 'RESTOCK' ? 'bg-green-500' :
                  slotProps.data.movement_type === 'TRANSFER' ? 'bg-blue-500' : 'bg-orange-500']">
                  {{ slotProps.data.movement_type }}
                </span>
              </template>
            </Column>
            <Column field="gadget_name" header="Gadget"></Column>
            <Column field="variant_sku" header="SKU"></Column>
            <Column header="Percorso">
              <template #body="slotProps">
                <span class="text-sm">
                  {{ slotProps.data.from_warehouse ? slotProps.data.from_warehouse.name : 'Esterno' }}
                  <i class="pi pi-arrow-right text-xs mx-2"></i>
                  {{ slotProps.data.to_warehouse ? slotProps.data.to_warehouse.name : 'Socio (Consegnato)' }}
                </span>
              </template>
            </Column>
            <Column field="quantity" header="Quantità">
              <template #body="slotProps">
                <span class="font-bold">{{ slotProps.data.quantity }} pz</span>
              </template>
            </Column>
            <Column field="notes" header="Note"></Column>
          </DataTable>
        </div>
      </div>
    </div>

    <!-- Movement Dialog -->
    <Dialog v-model:visible="showMovementDialog" header="Registra Movimento Magazzino" :modal="true" :style="{ width: '500px' }">
      <div class="flex flex-column gap-4 py-2 text-left">
        <!-- Gadget -->
        <div class="flex flex-column gap-2">
          <label for="m_gadget" class="font-semibold text-sm">Gadget *</label>
          <Select id="m_gadget" v-model="movementForm.gadget_id" :options="gadgets" optionLabel="name" optionValue="id" placeholder="Seleziona Gadget" class="w-full" />
        </div>

        <!-- Variant -->
        <div class="flex flex-column gap-2" v-if="movementForm.gadget_id">
          <label for="m_variant" class="font-semibold text-sm">Variante *</label>
          <Select id="m_variant" v-model="movementForm.variant_id" :options="variantsOptions" optionLabel="label" optionValue="value" placeholder="Seleziona Variante" class="w-full" />
        </div>

        <!-- Type -->
        <div class="flex flex-column gap-2">
          <label for="m_type" class="font-semibold text-sm">Tipo Movimento *</label>
          <Select id="m_type" v-model="movementForm.movement_type" :options="movementTypes" optionLabel="label" optionValue="value" class="w-full" />
        </div>

        <!-- From Warehouse -->
        <div class="flex flex-column gap-2" v-if="['TRANSFER', 'DELIVERY'].includes(movementForm.movement_type)">
          <label for="m_from" class="font-semibold text-sm">Magazzino Origine *</label>
          <Select id="m_from" v-model="movementForm.from_warehouse_id" :options="fromWarehouseOptions.filter(opt => opt.value !== movementForm.to_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.variant_id ? 'Seleziona Origine' : 'Seleziona prima una variante'" :disabled="!movementForm.variant_id" class="w-full" />
        </div>

        <!-- To Warehouse -->
        <div class="flex flex-column gap-2" v-if="['RESTOCK', 'TRANSFER'].includes(movementForm.movement_type)">
          <label for="m_to" class="font-semibold text-sm">Magazzino Destinazione *</label>
          <Select id="m_to" v-model="movementForm.to_warehouse_id" :options="toWarehouseOptions.filter(opt => opt.value !== movementForm.from_warehouse_id)" optionLabel="label" optionValue="value" :placeholder="movementForm.variant_id ? 'Seleziona Destinazione' : 'Seleziona prima una variante'" :disabled="!movementForm.variant_id" class="w-full" />
        </div>

        <!-- Quantity -->
        <div class="flex flex-column gap-2">
          <label for="m_qty" class="font-semibold text-sm">Quantità *</label>
          <InputNumber id="m_qty" v-model="movementForm.quantity" :min="1" placeholder="Quantità" class="w-full" showButtons />
        </div>

        <!-- Notes -->
        <div class="flex flex-column gap-2">
          <label for="m_notes" class="font-semibold text-sm">Note</label>
          <InputText id="m_notes" v-model="movementForm.notes" placeholder="Eventuali annotazioni..." class="w-full" />
        </div>
      </div>

      <template #footer>
        <Button label="Annulla" severity="secondary" outlined @click="showMovementDialog = false" />
        <Button label="Registra" severity="success" :loading="submitting" @click="submitMovement" />
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
</style>
