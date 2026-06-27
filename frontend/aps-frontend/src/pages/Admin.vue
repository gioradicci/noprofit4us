<script setup>
import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'

const toast = useToast()
const users = ref([])
const loading = ref(false)
const updatingUserId = ref(null)
const searchQuery = ref('')
const currentUserId = ref(null)

const roleOptions = [
  { label: 'Utente (USER)', value: 'USER' },
  { label: 'Socio (MEMBER)', value: 'MEMBER' },
  { label: 'Segretario (SECRETARY)', value: 'SECRETARY' },
  { label: 'Tesoriere (TREASURER)', value: 'TREASURER' },
  { label: 'Amministratore (ADMIN)', value: 'ADMIN' }
]

const filteredUsers = computed(() => {
  if (!searchQuery.value) return users.value
  const query = searchQuery.value.toLowerCase()
  return users.value.filter(u => {
    return (u.email || '').toLowerCase().includes(query) ||
           (u.first_name || '').toLowerCase().includes(query) ||
           (u.last_name || '').toLowerCase().includes(query) ||
           (u.phone || '').toLowerCase().includes(query) ||
           (u.role || '').toLowerCase().includes(query)
  })
})

async function loadUsers() {
  loading.value = true
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch("http://localhost:8000/users/", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    if (res.ok) {
      const data = await res.json()
      users.value = data.map(u => ({
        ...u,
        originalRole: u.role
      }))
    } else {
      toast.add({ severity: 'error', summary: 'Errore', detail: 'Impossibile caricare gli utenti', life: 3000 })
    }
  } catch (e) {
    console.error("Errore di caricamento utenti:", e)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore di connessione al server', life: 3000 })
  } finally {
    loading.value = false
  }
}

const confirm = useConfirm()

async function updateRole(user) {
  updatingUserId.value = user.id
  const newRole = user.role
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch(`http://localhost:8000/users/${user.id}/role`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ role: newRole })
    })
    
    if (res.ok) {
      const updatedUser = await res.json()
      // Aggiorna localmente
      user.role = updatedUser.role
      user.originalRole = updatedUser.role
      toast.add({ 
        severity: 'success', 
        summary: 'Ruolo Aggiornato', 
        detail: `Impostato ruolo ${newRole} per ${user.email}`, 
        life: 3000 
      })
    } else {
      const errData = await res.json()
      toast.add({ 
        severity: 'error', 
        summary: 'Aggiornamento Fallito', 
        detail: errData.detail || 'Impossibile modificare il ruolo', 
        life: 4000 
      })
      // Ricarica la lista per ripristinare il ruolo corretto in UI
      loadUsers()
    }
  } catch (e) {
    console.error("Errore di aggiornamento ruolo:", e)
    toast.add({ severity: 'error', summary: 'Errore', detail: 'Errore di connessione al server', life: 3000 })
    loadUsers()
  } finally {
    updatingUserId.value = null
  }
}

function revertRole(user) {
  user.role = user.originalRole
}

function confirmSave(user) {
  confirm.require({
    message: `Sei sicuro di voler cambiare il ruolo di ${user.email || 'questo utente'} da ${user.originalRole} a ${user.role}?`,
    header: 'Conferma Cambio Ruolo',
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: 'Salva',
    rejectLabel: 'Annulla',
    acceptProps: {
      severity: 'primary',
      label: 'Salva'
    },
    rejectProps: {
      severity: 'secondary',
      outlined: true
    },
    accept: () => {
      updateRole(user)
    },
    reject: () => {
      // Nessuna operazione
    }
  })
}

onMounted(async () => {
  const { data: { session } } = await supabase.auth.getSession()
  if (session) {
    currentUserId.value = session.user.id
  }
  loadUsers()
})
</script>

<template>
  <div class="py-6 px-4 max-w-7xl mx-auto">
    <!-- Header -->
    <div class="text-center mb-6">
      <h1 class="text-4xl font-extrabold text-900 mb-2">
        Gestione Ruoli & Permessi
      </h1>
      <p class="text-600 text-lg">
        Visualizza l'elenco degli utenti registrati e gestisci i ruoli per l'applicazione.
      </p>
    </div>

    <!-- Main Card -->
    <div class="card p-4 shadow-3 border-round-xl surface-card">
      
      <!-- Toolbar/Search -->
      <div class="flex flex-column sm:flex-row justify-content-between align-items-center gap-3 mb-4">
        <span class="p-input-icon-left w-full sm:w-20rem">
          <i class="pi pi-search" />
          <InputText 
            v-model="searchQuery" 
            placeholder="Cerca per email, nome, ruolo..." 
            class="w-full border-round-lg pl-5" 
          />
        </span>
        <Button 
          icon="pi pi-refresh" 
          label="Aggiorna" 
          class="p-button-outlined border-round-lg" 
          @click="loadUsers" 
          :loading="loading" 
        />
      </div>

      <!-- DataTable -->
      <DataTable 
        :value="filteredUsers" 
        :paginator="true" 
        :rows="10" 
        :loading="loading"
        responsiveLayout="scroll"
        class="p-datatable-striped"
        paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport RowsPerPageDropdown"
        currentPageReportTemplate="Mostrati {first} a {last} di {totalRecords} utenti"
      >
        <template #empty>
          <div class="text-center py-4 text-500">
            Nessun utente trovato.
          </div>
        </template>

        <!-- Email -->
        <Column field="email" header="Email" sortable class="font-medium text-800">
          <template #body="slotProps">
            <div class="flex align-items-center">
              <span>{{ slotProps.data.email || 'N/A' }}</span>
              <span v-if="slotProps.data.auth0_id === currentUserId" class="ml-2 px-2 py-1 text-xs border-round bg-blue-100 text-blue-800 font-semibold">
                Tu
              </span>
            </div>
          </template>
        </Column>

        <!-- Nome e Cognome -->
        <Column header="Nome e Cognome" sortable field="last_name">
          <template #body="slotProps">
            {{ slotProps.data.first_name || '' }} {{ slotProps.data.last_name || '' }}
            <span v-if="!slotProps.data.first_name && !slotProps.data.last_name" class="text-400 italic">
              Profilo non compilato
            </span>
          </template>
        </Column>

        <!-- Telefono -->
        <Column field="phone" header="Telefono">
          <template #body="slotProps">
            {{ slotProps.data.phone || '-' }}
          </template>
        </Column>

        <!-- Ruolo ed Edit -->
        <Column field="role" header="Ruolo Applicazione" sortable class="min-w-20rem">
          <template #body="slotProps">
            <div class="flex align-items-center gap-2">
              <Select 
                v-model="slotProps.data.role" 
                :options="roleOptions" 
                optionLabel="label" 
                optionValue="value"
                placeholder="Seleziona ruolo"
                class="w-full border-round-lg"
                :disabled="updatingUserId === slotProps.data.id || slotProps.data.auth0_id === currentUserId"
              />
              
              <!-- Se il ruolo è modificato rispetto all'originale, mostra i bottoni Salva e Annulla -->
              <template v-if="slotProps.data.role !== slotProps.data.originalRole && updatingUserId !== slotProps.data.id">
                <Button 
                  icon="pi pi-check" 
                  severity="success" 
                  class="p-button-rounded p-button-sm shadow-1" 
                  title="Salva modifiche" 
                  @click="confirmSave(slotProps.data)" 
                />
                <Button 
                  icon="pi pi-times" 
                  severity="secondary" 
                  class="p-button-rounded p-button-sm p-button-text" 
                  title="Annulla modifiche" 
                  @click="revertRole(slotProps.data)" 
                />
              </template>

              <i 
                v-if="updatingUserId === slotProps.data.id" 
                class="pi pi-spin pi-spinner text-primary text-lg" 
              />
            </div>
          </template>
        </Column>

      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.p-input-icon-left > i {
  left: 0.75rem;
}
.pl-5 {
  padding-left: 2.25rem !important;
}
</style>
