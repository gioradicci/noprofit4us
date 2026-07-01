<script setup>

import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { FilterMatchMode } from '@primevue/core/api'
import { useConfirm } from 'primevue/useconfirm';

const filters = ref({
  card_number: { value: null, matchMode: FilterMatchMode.CONTAINS },
  last_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  first_name : { value: null, matchMode: FilterMatchMode.CONTAINS },
  status: { value: null, matchMode: FilterMatchMode.EQUALS },
  membership_status: { value: null, matchMode: FilterMatchMode.EQUALS }
})

const statusOptions = [
  { label: 'PENDING', value: 'PENDING' },
  { label: 'APPROVED', value: 'APPROVED' },
  { label: 'PAID', value: 'PAID' },
  { label: 'INCOMPLETE', value: 'INCOMPLETE' },
  { label: 'REJECTED', value: 'REJECTED' }
]

const users = ref([])
const roles = ref([])
const filter = ref("ALL")  // ALL / PENDING / ACTIVE / EXPIRED
const confirm = useConfirm();

const filteredUsers = computed(() => {

  let result = users.value

  // ✅ filtro stato
  if (filter.value === "PENDING") {
    result = result.filter(u => u.status === "PENDING" || u.membership_status === "RENEWAL_PENDING")
  }

  if (filter.value === "ACTIVE") {
    result = result.filter(u => u.membership_status === "ACTIVE")
  }

  if (filter.value === "EXPIRED") {
    result = result.filter(u => u.membership_status === "EXPIRED")
  }
  return result
})

async function loadRoles() {
  const token = (await supabase.auth.getSession()).data.session?.access_token

  const payload = JSON.parse(atob(token.split('.')[1]))

  roles.value = payload.app_metadata?.roles || []

  //console.log("ROLES:", roles.value)
}

async function loadUsers() {
  const token = (await supabase.auth.getSession()).data.session?.access_token
  const res = await fetch(import.meta.env.VITE_API_URL + "/users/dashboard", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  users.value = await res.json()
}


function canApprove() {
  return roles.value.includes("ADMIN") || roles.value.includes("TREASURER")
}

const counts = computed(() => {
  return {
    total: users.value.length,
    pending: users.value.filter(u => u.status === "PENDING" || u.membership_status === "RENEWAL_PENDING").length,
    active: users.value.filter(u => u.membership_status === "ACTIVE").length,
    expired: users.value.filter(u => u.membership_status === "EXPIRED").length
  }
})



async function payAndApprove(id) {
  const token = (await supabase.auth.getSession()).data.session?.access_token

  await fetch(`${import.meta.env.VITE_API_URL}/users/${id}/pay-and-approve`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` }
  })

  loadUsers()
  loadRoles()
}


//  RINNOVA
async function renew(id) {
  const token = (await supabase.auth.getSession()).data.session?.access_token
  await fetch(`${import.meta.env.VITE_API_URL}/users/${id}/renew`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  loadUsers()
  loadRoles()
}

// ESPORTA IN EXCEL
async function exportUsersCSV() {
  const token = (await supabase.auth.getSession()).data.session?.access_token
  const res = await fetch(import.meta.env.VITE_API_URL + "/users/export", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  
  if (res.ok) {
    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'utenti.xlsx'
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } else {
    console.error("Errore durante l'esportazione", await res.text())
  }
}

function formatDate(date) {
  if (!date) return "-"

  return new Date(date).toLocaleDateString()
}
onMounted(() => {
  loadUsers()
  loadRoles()
})

//payAndApprove(slotProps.data.id)
const showConfirmDialog  = (id_user_to_accept) => {
    confirm.require({
        message: 'Vuoi confermare il pagamento e accettare l\'iscrizione del socio?',
        header: 'Conferm iscrizione socio',
        acceptLabel: "Il socio ha pagato, accetta l'iscrizione",
        icon: 'pi pi-exclamation-triangle',
        rejectLabel: 'Annulla',
         // Personalizza il bottone di conferma (es. Rosso/Pericolo)
        acceptProps: {
          severity: 'primary',
          label: 'Il socio ha pagato, accetta l\'iscrizione' // Puoi definirlo anche qui
        },
        
        // Personalizza il bottone di annullamento (es. Grigio/Secondario o Trasparente)
        rejectProps: {
          severity: 'secondary',
          outlined: true
        },
        accept: () => {
          payAndApprove(id_user_to_accept);
          //toast.add({ severity: 'success', summary: 'Eliminato', detail: 'Elemento eliminato con successo', life: 3000 });
        },
    });
};

const showRenewConfirmDialog  = (id_user_to_accept) => {
    confirm.require({
        message: 'Vuoi confermare il pagamento e accettare il rinnovo del socio?',
        header: 'Conferma rinnovo socio',
        acceptLabel: "Il socio ha pagato, accetta il rinnovo",
        icon: 'pi pi-exclamation-triangle',
        rejectLabel: 'Annulla',
        acceptProps: {
          severity: 'primary',
          label: 'Il socio ha pagato, accetta il rinnovo'
        },
        rejectProps: {
          severity: 'secondary',
          outlined: true
        },
        accept: () => {
          renew(id_user_to_accept);
        },
    });
};

async function rejectUser(id) {
  const token = (await supabase.auth.getSession()).data.session?.access_token
  try {
    const res = await fetch(`${import.meta.env.VITE_API_URL}/users/${id}/reject`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      loadUsers()
      loadRoles()
    } else {
      console.error("Errore durante il rifiuto dell'utente")
    }
  } catch (err) {
    console.error("Errore di rete durante il rifiuto dell'utente", err)
  }
}

const showRejectConfirmDialog = (id_user_to_reject) => {
    confirm.require({
        message: 'Vuoi rifiutare la richiesta di iscrizione del socio?',
        header: 'Rifiuta iscrizione socio',
        acceptLabel: 'Rifiuta iscrizione',
        icon: 'pi pi-exclamation-triangle',
        rejectLabel: 'Annulla',
        acceptProps: {
          severity: 'danger',
          label: 'Rifiuta iscrizione'
        },
        rejectProps: {
          severity: 'secondary',
          outlined: true
        },
        accept: () => {
          rejectUser(id_user_to_reject);
        },
    });
};

</script>
<template>
    <div class="py-5 px-3">
      <div class="text-center mb-5">
        <h2 class="font-bold text-3xl mb-2">
         Dashboard Soci
        </h2>
      </div>

      <div class="flex flex-wrap gap-4 justify-content-between mb-4">
        <div class="flex-1 min-w-12rem">
          <Card class="cursor-pointer shadow-2" @click="filter = 'Soci totali'">
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold">
                  {{ counts.total }}
                </div>
                <div>Soci totali</div>
              </div>
            </template>
          </Card>
        </div>
        <div class="flex-1 min-w-12rem">
          <Card 
            :pt="{
                root: { 
                  class: [
                    'cursor-pointer shadow-2 transition-colors duration-300', 
                      filter === 'PENDING' ? 'border-orange-500 bg-orange-50' : 'border-surface-300 bg-surface-0'
                  ] 
                }
              }"
           @click="filter = 'PENDING'">
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold text-orange-500">
                  {{ counts.pending }}
                </div>
                <div>Soci in attesa</div>
              </div>
            </template>
          </Card>
        </div>

        <div class="flex-1 min-w-12rem">
          <Card 
          :pt="{
                root: { 
                  class: [
                    'cursor-pointer shadow-2 transition-colors duration-300', 
                      filter === 'ACTIVE' ? 'border-green-500 bg-green-50' : 'border-surface-300 bg-surface-0'
                  ] 
                }
              }"
          @click="filter = 'ACTIVE'">
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold text-green-500">
                  {{ counts.active }}
                </div>
                <div>Soci attivi</div>
              </div>
            </template>
          </Card>
        </div>
        <div class="flex-1 min-w-12rem">
          <Card :pt="{
                root: { 
                  class: [
                    'cursor-pointer shadow-2 transition-colors duration-300', 
                      filter === 'EXPIRED' ? 'border-red-500 bg-red-50' : 'border-surface-300 bg-surface-0'
                  ] 
                }
              }" @click="filter = 'EXPIRED'" >
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold text-red-500">
                  {{ counts.expired }}
                </div>
                <div>Soci scaduti</div>
              </div>
            </template>
          </Card>
        </div>
    </div>

    <div class="grid mb-3 align-items-center">
      <!--  BOTTONI -->
      <div class="col-12 md:col-8 flex flex-wrap gap-2">
        <Button label="Tutti" @click="filter = 'ALL'" severity="info" />

        <Button
          label="Attesa accettazione"
          :severity="filter === 'PENDING' ? 'warn' : 'secondary'"
          @click="filter = 'PENDING'"
        />

        <Button
          label="Attivi"
          :severity="filter === 'ACTIVE' ? 'success' : 'secondary'"
          @click="filter = 'ACTIVE'"
        />

        <Button
          label="Scaduti"
          :severity="filter === 'EXPIRED' ? 'danger' : 'secondary'"
          @click="filter = 'EXPIRED'"
        />
      </div>

      <div class="col-12 md:col-4 flex justify-content-end" v-if="canApprove()">
        <Button label="Esporta libro soci" icon="pi pi-download" severity="help" @click="exportUsersCSV" />
      </div>
    </div>

        
    <DataTable
      :value="filteredUsers"
      v-model:filters="filters"
      filterDisplay="row"
      :globalFilterFields="['first_name', 'last_name']"
      paginator
      :rows="10"
      responsiveLayout="scroll"
      size="small"
      class="text-sm equal-cols"
    >
    <Column
        field="card_number"
        header="#tessera"
        sortable
        filter
        filterField="card_number"
        :showFilterMenu="false"
        :showClearButton="true"
      >
        <template #filter="{ filterModel, filterCallback }">
          <InputText
            v-model="filterModel.value"
            @input="filterCallback()"
            placeholder="N. tessera"
            class="w-full"
          />
        </template>
      </Column>

      <Column
          field="first_name"
          header="Nome"
          sortable
          filter
          filterField="first_name"
          :showFilterMenu="false"
          :showClearButton="true"
        >
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              @input="filterCallback()"
              placeholder="Cerca nome"
              class="w-full"
            />
          </template>
        </Column>
        <Column
          field="last_name"
          header="Cognome"
          sortable
          filter
          filterField="last_name"
          :showFilterMenu="false"
          :showClearButton="true"
        >
          <template #filter="{ filterModel, filterCallback }">
            <InputText
              v-model="filterModel.value"
              @input="filterCallback()"
              placeholder="Cerca cognome"
              class="w-full"
            />
          </template>
        </Column>


      <!-- STATUS UTENTE -->
      <Column
        field="status"
        header="Status"
        sortable
        filter
        :showFilterMenu="false"
      >

        <template #body="slotProps">
          <span :class="['badge', slotProps.data.status]">
            {{ slotProps.data.status }}
          </span>
        </template>

        <template #filter="{ filterModel, filterCallback }">
          <Select
            v-model="filterModel.value"
            :options="['PENDING', 'PAID', 'APPROVED', 'INCOMPLETE', 'REJECTED']"
            placeholder="Filtra"
            class="w-full"
            @change="filterCallback()"
            showClear
          />
        </template>

      </Column>

      <!-- STATUS MEMBERSHIP -->
      <Column
        field="membership_status"
        header="Membership"
        sortable
        filter
        :showFilterMenu="false"
      >
        <template #body="slotProps">
          <span :class="['badge', slotProps.data.membership_status]">
            {{ slotProps.data.membership_status }}
          </span>
        </template>

        <template #filter="{ filterModel, filterCallback }">
          <Select
            v-model="filterModel.value"
            :options="['ACTIVE', 'EXPIRED', 'RENEWAL_PENDING', 'NONE']"
            placeholder="Filtra"
            class="w-full"
            @change="filterCallback()"
            showClear
          />
        </template>
      </Column>
          
    <Column field="membership_end" header="Scadenza" sortable>
      <template #body="slotProps">
        {{ formatDate(slotProps.data.membership_end) }}
      </template>
    </Column>

      <!-- AZIONI -->
      <Column header="Azioni">
        <template #body="slotProps">
          <div class="flex gap-2">
            <Button class="multiline-btn"
              v-if="slotProps.data.status === 'PENDING' && canApprove()"
              label="Conferma Pagamento e registra socio"
              severity="success"
              @click="showConfirmDialog(slotProps.data.id)"
            >
            <div class="flex flex-column align-items-center">
                <span>Conferma Pagamento</span>
                <span>e registra socio</span>
              </div>
            </Button>

            <Button class="multiline-btn"
              v-if="slotProps.data.status === 'PENDING' && canApprove()"
              label="Rifiuta socio"
              severity="danger"
              @click="showRejectConfirmDialog(slotProps.data.id)"
            >
              <div class="flex flex-column align-items-center">
                <span>Rifiuta</span>
                <span>socio</span>
              </div>
            </Button>

            <Button class="multiline-btn"
              v-if="slotProps.data.membership_status === 'RENEWAL_PENDING' && canApprove()"
              severity="warning"
              @click="showRenewConfirmDialog(slotProps.data.id)"
            >
              <div class="flex flex-column align-items-center">
                <span>Conferma Pagamento</span>
                <span>e Rinnova</span>
              </div>
            </Button>
          </div>
        </template>
      </Column>

    </DataTable>
  </div>
</template>
<style>

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 1rem;
}
.multiline-btn {
  white-space: pre-line;
  flex-direction: column; /* Opzionale: se preferisci centrare gli elementi in verticale */
}

.badge {
  padding: 4px 10px;
  border-radius: 10px;
  color: white;
  font-size: 0.8rem;
}

/* ✅ USER STATUS */
.INCOMPLETE {
  background: gray;
}

.PENDING {
  background: orange;
}

.RENEWAL_PENDING {
  background: darkorange;
}

.PAID {
  background: yellowgreen;
}

.APPROVED {
  background: green;
}

.REJECTED {
  background: red;
}

/* ✅ MEMBERSHIP STATUS */
.ACTIVE {
  background: green;
}

.EXPIRED {
  background: red;
}

.NONE {
  background: gray;
}

.stats {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
}


.number {
  font-size: 1.8rem;
  font-weight: bold;
}

.label {
  font-size: 0.9rem;
  color: #666;
}

.selected {
  outline: 2px solid black;
}


.sorting {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

@media (min-width: 1024px) {
  .equal-cols .p-datatable-table {
    table-layout: fixed !important;
    width: 100% !important;
  }
  .equal-cols th, .equal-cols td {
    width: 14.28% !important;
  }
}

</style>
