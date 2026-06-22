<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

// PrimeVue Components
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

const { getAccessTokenSilently } = useAuth0()
const toast = useToast()
const confirm = useConfirm()

// State
const gadgets = ref([])
const loading = ref(false)
const showCreateWizard = ref(false)
const activeStep = ref("1")
const isEditMode = ref(false)

// New Gadget Form Data
const newGadget = ref({
  name: '',
  description: '',
  category: 'T-SHIRT',
  min_donation: 10.0
})

// Categories
const categories = [
  { label: 'T-Shirt', value: 'T-SHIRT' },
  { label: 'Cappellino', value: 'CAP' },
  { label: 'Portachiavi', value: 'KEYCHAIN' },
  { label: 'Spilla', value: 'PIN' },
  { label: 'Adesivo', value: 'STICKER' },
  { label: 'Poster', value: 'POSTER' },
  { label: 'Altro', value: 'OTHER' }
]

// Model options
const modelOptions = [
  { label: 'Nessuno / Vuoto', value: '' },
  { label: 'Uomo', value: 'Uomo' },
  { label: 'Donna', value: 'Donna' },
  { label: 'Unisex', value: 'Unisex' }
]

// New Variant Form Data
const newVariant = ref({
  size: '',
  color: '',
  model: '',
  variant_type: '',
  sku: '',
  price_modifier: 0.0
})

// Temporary list of variants to create
const tempVariants = ref([])

// Functions
async function loadGadgets() {
  loading.value = true
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch("http://localhost:8000/gadgets/", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    if (res.ok) {
      const data = await res.json()
      gadgets.value = data.map(g => ({
        ...g,
        total_stock: g.variants ? g.variants.reduce((acc, v) => acc + (v.stock_quantity || 0), 0) : 0
      }))
    } else {
      toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore nel caricamento dei gadget', life: 3000 })
    }
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Impossibile connettersi al server', life: 3000 })
  } finally {
    loading.value = false
  }
}

function startCreate() {
  isEditMode.value = false
  newGadget.value = {
    name: '',
    description: '',
    category: 'T-SHIRT',
    min_donation: 10.0
  }
  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0
  }
  tempVariants.value = []
  activeStep.value = "1"
  showCreateWizard.value = true
}

function startEdit(gadget) {
  isEditMode.value = true
  newGadget.value = {
    id: gadget.id,
    name: gadget.name,
    description: gadget.description || '',
    category: gadget.category,
    min_donation: gadget.min_donation
  }
  
  // Clone variants so modifications remain local until save
  tempVariants.value = gadget.variants.map(v => ({
    id: v.id,
    size: v.size || '',
    color: v.color || '',
    model: v.model || '',
    variant_type: v.variant_type || '',
    sku: v.sku || '',
    price_modifier: v.price_modifier || 0.0,
    stock_quantity: v.stock_quantity || 0
  }))

  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0
  }
  
  activeStep.value = "1"
  showCreateWizard.value = true
}

function addTempVariant() {
  if (!newVariant.value.sku) {
    // Auto-generate SKU if empty
    const cat = newGadget.value.category.substring(0, 3)
    const rand = Math.floor(1000 + Math.random() * 9000)
    newVariant.value.sku = `${cat}-${newVariant.value.size || 'UNI'}-${newVariant.value.color || 'GEN'}-${rand}`.toUpperCase()
  }
  
  tempVariants.value.push({ ...newVariant.value })
  
  // Reset variant form
  newVariant.value = {
    size: '',
    color: '',
    model: '',
    variant_type: '',
    sku: '',
    price_modifier: 0.0
  }
  toast.add({ severity: 'success', summary: 'Variante Aggiunta', detail: 'Variante aggiunta alla lista temporanea', life: 2000 })
}

function removeTempVariant(index) {
  const variant = tempVariants.value[index]
  if (isEditMode.value && variant.id && variant.stock_quantity > 0) {
    toast.add({
      severity: 'error',
      summary: 'Errore',
      detail: `Impossibile eliminare la variante SKU: ${variant.sku} poiché ha ${variant.stock_quantity} pezzi in magazzino.`,
      life: 5000
    })
    return
  }
  tempVariants.value.splice(index, 1)
}

async function saveGadgetAndVariants() {
  loading.value = true
  try {
    const token = await getAccessTokenSilently()
    
    if (isEditMode.value) {
      // 1. Update gadget
      const resGadget = await fetch(`http://localhost:8000/gadgets/${newGadget.value.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          name: newGadget.value.name,
          description: newGadget.value.description,
          category: newGadget.value.category,
          min_donation: newGadget.value.min_donation
        })
      })
      
      if (!resGadget.ok) {
        const errorData = await resGadget.json()
        const errorMsg = errorData.detail || "Errore durante la modifica del gadget"
        throw new Error(errorMsg)
      }
      
      // 2. Update variants
      const resVariants = await fetch(`http://localhost:8000/gadgets/${newGadget.value.id}/variants`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(tempVariants.value.map(v => ({
          id: v.id || null,
          size: v.size,
          color: v.color,
          model: v.model,
          variant_type: v.variant_type,
          sku: v.sku,
          price_modifier: v.price_modifier
        })))
      })
      
      if (!resVariants.ok) {
        const errorData = await resVariants.json()
        const errorMsg = errorData.detail || "Errore durante l'aggiornamento delle varianti"
        throw new Error(errorMsg)
      }
      
      toast.add({ severity: 'success', summary: 'Successo', detail: 'Gadget e varianti modificati con successo', life: 3000 })
    } else {
      // 1. Create gadget
      const resGadget = await fetch("http://localhost:8000/gadgets/", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(newGadget.value)
      })
      
      if (!resGadget.ok) {
        throw new Error("Errore durante la creazione del gadget")
      }
      
      const createdGadget = await resGadget.json()
      const gadgetId = createdGadget.id
      
      // 2. Create variants
      for (const variant of tempVariants.value) {
        const resVariant = await fetch("http://localhost:8000/gadgets/variants", {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          },
          body: JSON.stringify({
            gadget_id: gadgetId,
            ...variant
          })
        })
        if (!resVariant.ok) {
          toast.add({ severity: 'warn', summary: 'Attenzione', detail: `Impossibile creare la variante con SKU: ${variant.sku}`, life: 4000 })
        }
      }
      
      toast.add({ severity: 'success', summary: 'Successo', detail: 'Gadget e varianti creati con successo', life: 3000 })
    }
    
    showCreateWizard.value = false
    loadGadgets()
  } catch (err) {
    console.error(err)
    toast.add({ severity: 'error', summary: 'Errore', detail: err.message || 'Si è verificato un errore', life: 4000 })
  } finally {
    loading.value = false
  }
}

function confirmDelete(id, name) {
  // Check if gadget has any variants with stock_quantity > 0
  const gadget = gadgets.value.find(g => g.id === id)
  if (gadget && gadget.variants.some(v => v.stock_quantity > 0)) {
    toast.add({
      severity: 'error',
      summary: 'Eliminazione Bloccata',
      detail: `Impossibile eliminare "${name}" perché ci sono ancora pezzi in magazzino.`,
      life: 5000
    })
    return
  }

  confirm.require({
    message: `Sei sicuro di voler eliminare il gadget "${name}" e tutte le sue varianti?`,
    header: 'Conferma Eliminazione',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Sì, elimina',
    rejectLabel: 'Annulla',
    acceptProps: {
      severity: 'danger'
    },
    rejectProps: {
      severity: 'secondary',
      outlined: true
    },
    accept: async () => {
      try {
        const token = await getAccessTokenSilently()
        const res = await fetch(`http://localhost:8000/gadgets/${id}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
        if (res.ok) {
          toast.add({ severity: 'success', summary: 'Eliminato', detail: 'Gadget eliminato con successo', life: 3000 })
          loadGadgets()
        } else {
          const errorMsg = res.status === 400 ? await res.text() : 'Impossibile eliminare il gadget'
          toast.add({ severity: 'error', summary: 'Errore', detail: errorMsg, life: 3000 })
        }
      } catch (err) {
        console.error(err)
        toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore di connessione', life: 3000 })
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
        <h2 class="font-bold text-3xl mb-1 text-900">Gestione Gadget</h2>
        <p class="text-secondary text-sm m-0">Visualizza, crea e organizza i gadget dell'associazione e le loro varianti</p>
      </div>
      <Button v-if="!showCreateWizard" label="Nuovo Gadget" icon="pi pi-plus" severity="primary" @click="startCreate" />
      <Button v-else label="Annulla" icon="pi pi-times" severity="secondary" outlined @click="showCreateWizard = false" />
    </div>

    <!-- Wizard Creazione -->
    <div v-if="showCreateWizard" class="card p-4 shadow-2 border-round surface-card mb-5">
      <h3 class="text-xl font-bold mb-4 text-primary">{{ isEditMode ? 'Modifica Gadget & Caratteristiche' : 'Nuovo Gadget & Caratteristiche' }}</h3>
      <Stepper v-model:value="activeStep">
        <StepList class="mb-4">
          <Step value="1">1. Dati Generali</Step>
          <Step value="2">2. Varianti & Caratteristiche</Step>
          <Step value="3">3. Conferma</Step>
        </StepList>

        <StepPanels>
          <!-- STEP 1: Dati Generali -->
          <StepPanel v-slot="{ activateCallback }" value="1">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="name" class="font-semibold text-sm">Nome Gadget *</label>
                <InputText id="name" v-model="newGadget.name" placeholder="Es. T-Shirt Ufficiale APS" class="w-full" />
              </div>
              
              <div class="grid">
                <div class="col-12 md:col-6 flex flex-column gap-2">
                  <label for="category" class="font-semibold text-sm">Categoria *</label>
                  <Select id="category" v-model="newGadget.category" :options="categories" optionLabel="label" optionValue="value" class="w-full" />
                </div>
                
                <div class="col-12 md:col-6 flex flex-column gap-2">
                  <label for="min_donation" class="font-semibold text-sm">Donazione Minima (€) *</label>
                  <InputNumber id="min_donation" v-model="newGadget.min_donation" :min="0" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" />
                </div>
              </div>

              <div class="flex flex-column gap-2">
                <label for="description" class="font-semibold text-sm">Descrizione</label>
                <InputText id="description" v-model="newGadget.description" placeholder="Descrizione o dettagli aggiuntivi..." class="w-full" />
              </div>
            </div>
            
            <div class="flex pt-4 justify-content-end border-top-1 border-light">
              <Button label="Avanti" icon="pi pi-arrow-right" iconPos="right" :disabled="!newGadget.name || !newGadget.category || newGadget.min_donation === null" @click="activateCallback('2')" />
            </div>
          </StepPanel>

          <!-- STEP 2: Varianti -->
          <StepPanel v-slot="{ activateCallback }" value="2">
            <div class="grid py-3">
              <!-- Form Nuova Variante -->
              <div class="col-12 lg:col-4 border-right-none lg:border-right-1 border-light pr-0 lg:pr-4">
                <h4 class="font-bold text-lg mb-3 text-700">Aggiungi Variante</h4>
                
                <div class="flex flex-column gap-3 text-left">
                  <div class="flex flex-column gap-1">
                    <label for="v_size" class="text-xs font-semibold">Taglia (Size)</label>
                    <InputText id="v_size" v-model="newVariant.size" placeholder="Es. S, M, L, XL" class="w-full" size="small" />
                  </div>
                  
                  <div class="flex flex-column gap-1">
                    <label for="v_color" class="text-xs font-semibold">Colore</label>
                    <InputText id="v_color" v-model="newVariant.color" placeholder="Es. Rosso, Blu" class="w-full" size="small" />
                  </div>

                  <div class="flex flex-column gap-1">
                    <label for="v_model" class="text-xs font-semibold">Modello</label>
                    <Select id="v_model" v-model="newVariant.model" :options="modelOptions" optionLabel="label" optionValue="value" placeholder="Seleziona Modello" class="w-full" size="small" />
                  </div>

                  <div class="flex flex-column gap-1">
                    <label for="v_type" class="text-xs font-semibold">Tipo Variante / Extra</label>
                    <InputText id="v_type" v-model="newVariant.variant_type" placeholder="Es. Cotone Bio, Spilla Metallo" class="w-full" size="small" />
                  </div>

                  <div class="flex flex-column gap-1">
                    <label for="v_sku" class="text-xs font-semibold">SKU (Codice Univoco)</label>
                    <InputText id="v_sku" v-model="newVariant.sku" placeholder="Lascia vuoto per autogenerare" class="w-full" size="small" />
                  </div>

                  <div class="flex flex-column gap-1">
                    <label for="v_price" class="text-xs font-semibold">Modificatore Prezzo (€)</label>
                    <InputNumber id="v_price" v-model="newVariant.price_modifier" :minFractionDigits="2" :maxFractionDigits="2" class="w-full" mode="currency" currency="EUR" locale="it-IT" size="small" />
                  </div>

                  <Button label="Aggiungi Variante" icon="pi pi-plus" severity="success" size="small" class="mt-2" @click="addTempVariant" />
                </div>
              </div>

              <!-- Lista Varianti Inserite -->
              <div class="col-12 lg:col-8 pl-0 lg:pl-4 mt-4 lg:mt-0">
                <h4 class="font-bold text-lg mb-3 text-700">Varianti ({{ tempVariants.length }})</h4>
                
                <DataTable :value="tempVariants" class="p-datatable-sm" responsiveLayout="scroll" emptyMessage="Nessuna variante aggiunta. I gadget semplici possono avere anche una singola variante generica.">
                  <Column field="sku" header="SKU">
                    <template #body="slotProps">
                      <InputText v-model="slotProps.data.sku" class="w-full" size="small" />
                    </template>
                  </Column>
                  <Column field="size" header="Taglia">
                    <template #body="slotProps">
                      <InputText v-model="slotProps.data.size" class="w-full" size="small" />
                    </template>
                  </Column>
                  <Column field="color" header="Colore">
                    <template #body="slotProps">
                      <InputText v-model="slotProps.data.color" class="w-full" size="small" />
                    </template>
                  </Column>
                  <Column field="model" header="Modello">
                    <template #body="slotProps">
                      <Select v-model="slotProps.data.model" :options="modelOptions" optionLabel="label" optionValue="value" class="w-full" size="small" />
                    </template>
                  </Column>
                  <Column field="price_modifier" header="Extra Prezzo">
                    <template #body="slotProps">
                      <InputNumber v-model="slotProps.data.price_modifier" :minFractionDigits="2" :maxFractionDigits="2" mode="currency" currency="EUR" locale="it-IT" class="w-full" size="small" />
                    </template>
                  </Column>
                  <Column header="Azioni">
                    <template #body="slotProps">
                      <Button icon="pi pi-trash" severity="danger" text rounded @click="removeTempVariant(slotProps.index)" />
                    </template>
                  </Column>
                </DataTable>
              </div>
            </div>

            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('1')" />
              <Button label="Avanti" icon="pi pi-arrow-right" iconPos="right" :disabled="tempVariants.length === 0" @click="activateCallback('3')" />
            </div>
          </StepPanel>

          <!-- STEP 3: Riepilogo e Conferma -->
          <StepPanel v-slot="{ activateCallback }" value="3">
            <div class="py-3 text-left">
              <h4 class="font-bold text-lg mb-3 text-700">{{ isEditMode ? 'Riepilogo Modifiche Gadget' : 'Riepilogo Nuovo Gadget' }}</h4>
              
              <div class="surface-ground p-4 border-round grid row-gap-3 mb-4">
                <div class="col-12 md:col-6 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-color-secondary uppercase">Nome Gadget</span>
                  <span class="text-base text-900 font-medium">{{ newGadget.name }}</span>
                </div>
                <div class="col-12 md:col-6 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-color-secondary uppercase">Categoria</span>
                  <span class="text-base text-900 font-medium">{{ newGadget.category }}</span>
                </div>
                <div class="col-12 md:col-6 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-color-secondary uppercase">Donazione Minima Base</span>
                  <span class="text-base text-primary font-bold">{{ newGadget.min_donation.toFixed(2) }} €</span>
                </div>
                <div class="col-12 md:col-6 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-color-secondary uppercase">Descrizione</span>
                  <span class="text-base text-900 font-medium">{{ newGadget.description || '-' }}</span>
                </div>
              </div>

              <h4 class="font-bold text-lg mb-3 text-700">{{ isEditMode ? 'Varianti modificate' : 'Varianti da creare' }}</h4>
              <DataTable :value="tempVariants" class="p-datatable-sm" responsiveLayout="scroll">
                <Column field="sku" header="SKU"></Column>
                <Column field="size" header="Taglia"></Column>
                <Column field="color" header="Colore"></Column>
                <Column field="model" header="Modello"></Column>
                <Column field="price_modifier" header="Prezzo Finale">
                  <template #body="slotProps">
                    {{ (newGadget.min_donation + slotProps.data.price_modifier).toFixed(2) }} €
                  </template>
                </Column>
              </DataTable>
            </div>

            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('2')" />
              <Button :label="isEditMode ? 'Salva Modifiche' : 'Crea Gadget & Varianti'" icon="pi pi-check" severity="success" :loading="loading" @click="saveGadgetAndVariants" />
            </div>
          </StepPanel>
        </StepPanels>
      </Stepper>
    </div>

    <!-- Lista Gadget Esistenti -->
    <div v-else class="card p-4 shadow-2 border-round surface-card">
      <DataTable :value="gadgets" :loading="loading" paginator :rows="10" responsiveLayout="scroll">
        <template #empty>
          <div class="text-center py-4">
            <i class="pi pi-box text-4xl text-300 mb-2"></i>
            <p class="m-0 text-color-secondary">Nessun gadget presente nel database. Clicca su "Nuovo Gadget" per iniziare.</p>
          </div>
        </template>
        
        <Column field="name" header="Nome" sortable class="font-bold"></Column>
        
        <Column field="category" header="Categoria" sortable>
          <template #body="slotProps">
            <span class="badge border-round px-2 py-1 text-xs bg-cyan-100 text-cyan-800">
              {{ slotProps.data.category }}
            </span>
          </template>
        </Column>
        
        <Column field="min_donation" header="Donazione Min." sortable>
          <template #body="slotProps">
            {{ slotProps.data.min_donation.toFixed(2) }} €
          </template>
        </Column>

        <Column field="description" header="Descrizione"></Column>
        
        <Column header="Varianti Attive">
          <template #body="slotProps">
            <div class="flex flex-wrap gap-1">
              <span v-for="v in slotProps.data.variants" :key="v.id" class="text-xs bg-light border-round px-2 py-1" :title="`SKU: ${v.sku}`">
                {{ v.size || '' }} {{ v.color || '' }} {{ v.model || '' }}
                <span :class="['font-semibold ml-1', v.stock_quantity < 1 ? 'text-red-500' : '']">({{ v.stock_quantity }} pz)</span>
              </span>
            </div>
          </template>
        </Column>

        <Column field="total_stock" header="Totale Giacenza" sortable>
          <template #body="slotProps">
            <span :class="['font-bold', slotProps.data.total_stock < 1 ? 'text-red-500' : 'text-900']">
              {{ slotProps.data.total_stock }} pz
            </span>
          </template>
        </Column>

        <Column header="Azioni">
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
</style>
