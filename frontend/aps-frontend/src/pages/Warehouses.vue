<script setup>
import { API_URL } from '../config.js'
import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Dialog from 'primevue/dialog'
import Select from 'primevue/select'


const toast = useToast()
const confirm = useConfirm()

// State
const warehouses = ref([])
const loading = ref(false)
const submitting = ref(false)
const showDialog = ref(false)
const isEditMode = ref(false)
const currentWarehouseId = ref(null)

const showTransferDialog = ref(false)
const transferForm = ref({
  from_warehouse_id: null,
  from_warehouse_name: '',
  from_warehouse_code: '',
  to_warehouse_id: null,
  notes: ''
})
const transferring = ref(false)

const targetWarehouseOptions = computed(() => {
  return warehouses.value.filter(
    w => w.id !== transferForm.value.from_warehouse_id && w.is_active !== false
  )
})

const warehouseForm = ref({
  code: '',
  name: '',
  is_active: true
})

const activeOptions = [
  { label: 'Attivo', value: true },
  { label: 'Disattivato', value: false }
]

// Load warehouses
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
      toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore nel caricamento dei magazzini', life: 3000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Impossibile connettersi al server', life: 3000 })
  } finally {
    loading.value = false
  }
}

// Dialog management
function openCreate() {
  isEditMode.value = false
  currentWarehouseId.value = null
  warehouseForm.value = {
    code: '',
    name: '',
    is_active: true
  }
  showDialog.value = true
}

// Edit Dialog
function openEdit(wh) {
  isEditMode.value = true
  currentWarehouseId.value = wh.id
  warehouseForm.value = {
    code: wh.code,
    name: wh.name,
    is_active: wh.is_active
  }
  showDialog.value = true
}

// Save (create or update)
async function saveWarehouse() {
  if (!warehouseForm.value.code || !warehouseForm.value.name) {
    toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Compilare tutti i campi obbligatori', life: 3000 })
    return
  }

  submitting.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const method = isEditMode.value ? 'PUT' : 'POST'
    const url = isEditMode.value 
      ? `${API_URL}/gadgets/warehouses/${currentWarehouseId.value}`
      : API_URL + '/gadgets/warehouses'

    const res = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(warehouseForm.value)
    })

    const data = await res.json()

    if (res.ok) {
      toast.add({ 
        severity: 'success', 
        summary: 'Successo', 
        detail: isEditMode.value ? 'Magazzino aggiornato con successo' : 'Magazzino creato con successo', 
        life: 3000 
      })
      showDialog.value = false
      loadWarehouses()
    } else {
      toast.add({ 
        severity: 'error', 
        summary: 'Errore', 
        detail: data.detail || 'Impossibile salvare il magazzino', 
        life: 4000 
      })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore durante la connessione al server', life: 3000 })
  } finally {
    submitting.value = false
  }
}

// Delete warehouse
async function deleteWarehouse(id) {
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(`${API_URL}/gadgets/warehouses/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    })
    
    const data = await res.json()

    if (res.ok) {
      toast.add({ severity: 'success', summary: 'Successo', detail: 'Magazzino eliminato con successo', life: 3000 })
      loadWarehouses()
    } else {
      toast.add({ 
        severity: 'error', 
        summary: 'Errore', 
        detail: data.detail || 'Impossibile eliminare il magazzino', 
        life: 4000 
      })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore durante la connessione al server', life: 3000 })
  }
}

function confirmDelete(wh) {
  confirm.require({
    message: `Sei sicuro di voler eliminare il magazzino ${wh.name} (${wh.code})? L'operazione non è reversibile.`,
    header: 'Conferma Eliminazione',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Sì, elimina',
    rejectLabel: 'Annulla',
    acceptProps: { severity: 'danger' },
    accept: () => deleteWarehouse(wh.id)
  })
}

function openBulkTransfer(wh) {
  transferForm.value = {
    from_warehouse_id: wh.id,
    from_warehouse_name: wh.name,
    from_warehouse_code: wh.code,
    to_warehouse_id: null,
    notes: ''
  }
  showTransferDialog.value = true
}

async function executeBulkTransfer() {
  if (!transferForm.value.to_warehouse_id) {
    toast.add({ severity: 'warn', summary: 'Attenzione', detail: 'Seleziona il magazzino di destinazione', life: 3000 })
    return
  }

  transferring.value = true
  try {
    const token = (await supabase.auth.getSession()).data.session?.access_token
    const res = await fetch(API_URL + '/gadgets/warehouses/bulk-transfer', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({
        from_warehouse_id: transferForm.value.from_warehouse_id,
        to_warehouse_id: transferForm.value.to_warehouse_id,
        notes: transferForm.value.notes
      })
    })

    const data = await res.json()

    if (res.ok) {
      toast.add({ 
        severity: 'success', 
        summary: 'Successo', 
        detail: `Trasferiti con successo ${data.transferred_quantity} pezzi.`, 
        life: 3000 
      })
      showTransferDialog.value = false
      loadWarehouses()
    } else {
      toast.add({ 
        severity: 'error', 
        summary: 'Errore', 
        detail: data.detail || 'Impossibile completare il trasferimento', 
        life: 4000 
      })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore durante la connessione al server', life: 3000 })
  } finally {
    transferring.value = false
  }
}

onMounted(() => {
  loadWarehouses()
})
</script>

<template>
  <div class="warehouses-container py-5 px-3">
    <!-- Header -->
    <div class="flex justify-content-between align-items-center mb-5">
      <div>
        <h2 class="font-bold text-3xl mb-1 text-900">Gestione Magazzini</h2>
        <p class="text-secondary text-sm m-0">Crea, modifica e disattiva i magazzini per lo stoccaggio dei gadget dell'associazione</p>
      </div>
      <Button label="Nuovo Magazzino" icon="pi pi-plus" severity="primary" @click="openCreate" />
    </div>

    <!-- Table -->
    <div class="card p-4 shadow-2 border-round surface-card">
      <DataTable :value="warehouses" :loading="loading" paginator :rows="10" responsiveLayout="scroll" class="text-sm">
        <template #empty>
          <div class="text-center py-4">
            <i class="pi pi-building text-3xl text-400 mb-2"></i>
            <p class="m-0 text-color-secondary">Nessun magazzino configurato.</p>
          </div>
        </template>

        <Column field="code" header="Codice" sortable class="font-bold"></Column>
        <Column field="name" header="Nome Magazzino" sortable></Column>
        <Column field="total_stock" header="Pezzi in Giacenza" sortable class="text-center">
          <template #body="slotProps">
            <span :class="['font-semibold', (slotProps.data.total_stock ?? 0) > 0 ? 'text-green-600' : 'text-red-500']">
              {{ slotProps.data.total_stock ?? 0 }} pz
            </span>
          </template>
        </Column>
        <Column field="is_active" header="Stato" sortable>
          <template #body="slotProps">
            <span :class="['badge', slotProps.data.is_active ? 'bg-green-500' : 'bg-gray-500']">
              {{ slotProps.data.is_active ? 'Attivo' : 'Disattivato' }}
            </span>
          </template>
        </Column>
        
        <Column header="Azioni" class="text-right">
          <template #body="slotProps">
            <div class="flex gap-2 justify-content-end">
              <Button 
                v-if="slotProps.data.total_stock > 0" 
                icon="pi pi-directions" 
                severity="warn" 
                outlined 
                size="small" 
                title="Trasferimento massivo"
                @click="openBulkTransfer(slotProps.data)" 
              />
              <Button icon="pi pi-pencil" severity="secondary" title="Modifica magazzino" outlined size="small" @click="openEdit(slotProps.data)" />
              <Button icon="pi pi-trash" severity="danger" title="Cancella magazzino" outlined size="small" @click="confirmDelete(slotProps.data)" />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Create/Edit Dialog -->
    <Dialog v-model:visible="showDialog" :header="isEditMode ? 'Modifica Magazzino' : 'Nuovo Magazzino'" :modal="true" :style="{ width: '400px' }">
      <div class="flex flex-column gap-4 py-2 text-left">
        <!-- Code -->
        <div class="flex flex-column gap-2">
          <label for="w_code" class="font-semibold text-sm">Codice Magazzino *</label>
          <InputText id="w_code" v-model="warehouseForm.code" placeholder="Es. MAIN, NORD, SUD" class="w-full" />
          <small class="text-color-secondary">Identificativo unico in maiuscolo.</small>
        </div>

        <!-- Name -->
        <div class="flex flex-column gap-2">
          <label for="w_name" class="font-semibold text-sm">Nome Magazzino *</label>
          <InputText id="w_name" v-model="warehouseForm.name" placeholder="Es. Magazzino Centrale" class="w-full" />
        </div>

        <!-- Is Active -->
        <div class="flex flex-column gap-2" v-if="isEditMode">
          <label for="w_active" class="font-semibold text-sm">Stato Magazzino</label>
          <Select id="w_active" v-model="warehouseForm.is_active" :options="activeOptions" optionLabel="label" optionValue="value" class="w-full" />
          <small class="text-color-secondary">I magazzini disattivati non possono ricevere nuovi stock, ma permettono di svuotare le giacenze esistenti.</small>
        </div>
      </div>

      <template #footer>
        <Button label="Annulla" severity="secondary" outlined @click="showDialog = false" />
        <Button label="Salva" severity="success" :loading="submitting" @click="saveWarehouse" />
      </template>
    </Dialog>

    <!-- Bulk Transfer Dialog -->
    <Dialog v-model:visible="showTransferDialog" header="Trasferimento Massivo Scorte" :modal="true" :style="{ width: '450px' }">
      <div class="flex flex-column gap-4 py-2 text-left">
        <div class="p-3 border-round flex gap-3 align-items-center" style="background-color: #fffbeb; border: 1px solid #fde68a; color: #b45309; font-size: 0.9rem;">
          <i class="pi pi-exclamation-triangle text-xl"></i>
          <div>
            Stai per trasferire <strong>tutti</strong> gli articoli con giacenza dal magazzino 
            <strong>{{ transferForm.from_warehouse_name }} ({{ transferForm.from_warehouse_code }})</strong>.
          </div>
        </div>

        <!-- Destination Warehouse -->
        <div class="flex flex-column gap-2">
          <label for="to_wh" class="font-semibold text-sm">Magazzino di Destinazione *</label>
          <Select 
            id="to_wh" 
            v-model="transferForm.to_warehouse_id" 
            :options="targetWarehouseOptions" 
            optionLabel="name" 
            optionValue="id" 
            placeholder="Seleziona magazzino di destinazione..." 
            class="w-full" 
          />
          <small class="text-color-secondary">Vengono proposti solo i magazzini attivi diversi da quello di origine.</small>
        </div>

        <!-- Notes -->
        <div class="flex flex-column gap-2">
          <label for="transfer_notes" class="font-semibold text-sm">Note</label>
          <InputText id="transfer_notes" v-model="transferForm.notes" placeholder="Es. Spostamento per dismissione filiale" class="w-full" />
        </div>
      </div>

      <template #footer>
        <Button label="Annulla" severity="secondary" outlined @click="showTransferDialog = false" />
        <Button label="Conferma Trasferimento" severity="warn" :loading="transferring" @click="executeBulkTransfer" />
      </template>
    </Dialog>
  </div>
</template>

<style scoped>
.warehouses-container {
  max-width: 900px;
  margin: 0 auto;
}

.badge {
  padding: 4px 10px;
  border-radius: 10px;
  color: white;
  font-size: 0.8rem;
  font-weight: 500;
}

.bg-green-500 {
  background-color: #22c55e !important;
}

.bg-gray-500 {
  background-color: #6b7280 !important;
}
</style>
