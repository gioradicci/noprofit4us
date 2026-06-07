<script setup>
const { getAccessTokenSilently } = useAuth0()
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { FilterMatchMode } from '@primevue/core/api'

const filters = ref({
  first_name: { value: null, matchMode: FilterMatchMode.CONTAINS },
  last_name: { value: null, matchMode: FilterMatchMode.CONTAINS },

  status: { value: null, matchMode: FilterMatchMode.EQUALS },
  membership_status: { value: null, matchMode: FilterMatchMode.EQUALS }
})

const statusOptions = [
  { label: 'PENDING', value: 'PENDING' },
  { label: 'APPROVED', value: 'APPROVED' },
  { label: 'PAID', value: 'PAID' },
  { label: 'INCOMPLETE', value: 'INCOMPLETE' }
]


const users = ref([])
const roles = ref([])
const filter = ref("ALL")  // ALL / PENDING / ACTIVE / EXPIRED


const filteredUsers = computed(() => {

  let result = users.value

  // ✅ filtro stato
  if (filter.value === "PENDING") {
    result = result.filter(u => u.status === "PENDING")
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
  const token = await getAccessTokenSilently()

  const payload = JSON.parse(atob(token.split('.')[1]))

  roles.value = payload["https://aps/roles"] || []

  //console.log("ROLES:", roles.value)
}

async function loadUsers() {
  const token = await getAccessTokenSilently()
  const res = await fetch("http://localhost:8000/users/dashboard", {
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
    pending: users.value.filter(u => u.status === "PENDING").length,
    active: users.value.filter(u => u.membership_status === "ACTIVE").length,
    expired: users.value.filter(u => u.membership_status === "EXPIRED").length
  }
})



async function payAndApprove(id) {
  const token = await getAccessTokenSilently()

  await fetch(`http://localhost:8000/users/${id}/pay-and-approve`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}` }
  })

  loadUsers()
  loadRoles()
}


//  RINNOVA
async function renew(id) {
  const token = await getAccessTokenSilently()
  await fetch(`http://localhost:8000/users/${id}/renew`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`
    }
  })
  loadUsers()
  loadRoles()
}

function formatDate(date) {
  if (!date) return "-"

  return new Date(date).toLocaleDateString()
}
onMounted(() => {
  loadUsers()
  loadRoles()
})

</script>
<template>
    <div>
      <h2>Dashboard Soci</h2>

      <div class="flex flex-wrap gap-4 justify-content-between mb-4">
        <div class="flex-1 min-w-12rem">
          <Card class="cursor-pointer shadow-2" @click="filter = 'Soci totali'">
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold">
                  {{ counts.total }}
                </div>
                <div>Totali</div>
              </div>
            </template>
          </Card>
        </div>
        <div class="flex-1 min-w-12rem pending">
          <Card class="cursor-pointer shadow-2" @click="filter = 'PENDING'">
            <template #content>
              <div class="text-center">
                <div class="text-2xl font-bold text-orange-500">
                  {{ counts.pending }}
                </div>
                <div>Attesa accettazione</div>
              </div>
            </template>
          </Card>
        </div>

        <div class="flex-1 min-w-12rem active">
          <Card class="cursor-pointer shadow-2" @click="filter = 'ACTIVE'">
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

        <div class="flex-1 min-w-12rem expired">
          <Card class="cursor-pointer shadow-2" @click="filter = 'EXPIRED'">
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
    </div>

        
    <DataTable
      :value="filteredUsers"
      v-model:filters="filters"
      filterDisplay="row"
      globalFilterFields="['first_name', 'last_name']"
      paginator
      :rows="10"
      responsiveLayout="scroll"
    >

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
          <Dropdown
            v-model="filterModel.value"
            :options="['PENDING', 'PAID','APPROVED', 'INCOMPLETE']"
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
          <Dropdown
            v-model="filterModel.value"
            :options="['ACTIVE', 'EXPIRED', 'NONE']"
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

          <Button class="multiline-btn"
            v-if="slotProps.data.status === 'PENDING' && canApprove()"
            label="Conferma Pagamento e registra socio"
            severity="success"
            @click="payAndApprove(slotProps.data.id)"
          >
          <div class="flex flex-column align-items-center">
              <span>Conferma Pagamento</span>
              <span>e registra socio</span>
            </div>
          </Button>

          <Button
            v-if="slotProps.data.membership_status === 'EXPIRED' && canApprove()"
            label="Rinnova"
            severity="warning"
            icon="pi pi-refresh"
            @click="renew(slotProps.data.id)"
          />

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

.PAID {
  background: yellowgreen;
}

.APPROVED {
  background: green;
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

/* colori */
.pending { border-top: 4px solid orange; border-radius: 15%;}
.active { border-top: 4px solid green; border-radius: 15%;}
.expired { border-top: 4px solid red; border-radius: 15%;}

.selected {
  outline: 2px solid black;
}


.sorting {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

</style>
