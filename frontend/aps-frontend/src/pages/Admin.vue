<script setup>
import { API_URL } from '../config.js'
import { ref, onMounted, computed } from 'vue'
import { supabase } from '../supabase'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const toast = useToast()
const confirm = useConfirm()

const users = ref([])
const loading = ref(false)
const updatingUserId = ref(null)
const searchQuery = ref('')
const currentUserId = ref(null)
const editingUserId = ref(null)
const editForm = ref({
  first_name: '',
  last_name: '',
  phone: ''
})

const roleOptions = [
  { label: t('admin.roles.user'), value: 'USER' },
  { label: t('admin.roles.member'), value: 'MEMBER' },
  { label: t('admin.roles.secretary'), value: 'SECRETARY' },
  { label: t('admin.roles.treasurer'), value: 'TREASURER' },
  { label: t('admin.roles.admin'), value: 'ADMIN' }
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
    const res = await fetch(API_URL + "/users/", {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const data = await res.json()
      users.value = data.map(u => ({
        ...u,
        originalRole: u.role
      }))
    } else {
      toast.add({ severity: 'error', summary: t('common.error'), detail: t('admin.errors.loadFailed'), life: 3000 })
    }
  } catch (e) {
    console.error("Errore di caricamento utenti:", e)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('admin.errors.connectionFailed'), life: 3000 })
  } finally {
    loading.value = false
  }
}

async function updateRole(user) {
  updatingUserId.value = user.id
  const newRole = user.role
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch(`${API_URL}/users/${user.id}/role`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ role: newRole })
    })
    if (res.ok) {
      const updatedUser = await res.json()
      user.role = updatedUser.role
      user.originalRole = updatedUser.role
      toast.add({
        severity: 'success',
        summary: t('admin.roleUpdated'),
        detail: t('admin.roleUpdatedDetail', { role: newRole, email: user.email }),
        life: 3000
      })
    } else {
      const errData = await res.json()
      toast.add({
        severity: 'error',
        summary: t('admin.updateFailed'),
        detail: errData.detail || t('admin.errors.updateFailed'),
        life: 4000
      })
      loadUsers()
    }
  } catch (e) {
    console.error("Errore di aggiornamento ruolo:", e)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('admin.errors.connectionFailed'), life: 3000 })
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
    message: t('admin.confirmMessage', { email: user.email, fromRole: user.originalRole, toRole: user.role }),
    header: t('admin.confirmHeader'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('common.save'),
    rejectLabel: t('common.cancel'),
    acceptProps: { severity: 'primary', label: t('common.save') },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: () => { updateRole(user) }
  })
}

function startEdit(user) {
  editingUserId.value = user.id
  editForm.value = {
    first_name: user.first_name || '',
    last_name: user.last_name || '',
    phone: user.phone || ''
  }
}

function cancelEdit() {
  editingUserId.value = null
  editForm.value = { first_name: '', last_name: '', phone: '' }
}

async function saveEdit(user) {
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch(`${API_URL}/users/${user.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        first_name: editForm.value.first_name,
        last_name: editForm.value.last_name,
        phone: editForm.value.phone
      })
    })
    if (res.ok) {
      const updatedUser = await res.json()
      user.first_name = updatedUser.first_name
      user.last_name = updatedUser.last_name
      user.phone = updatedUser.phone
      toast.add({ severity: 'success', summary: t('common.success'), detail: t('admin.editSuccess'), life: 3000 })
      cancelEdit()
    } else {
      const errData = await res.json()
      toast.add({ severity: 'error', summary: t('common.error'), detail: errData.detail || t('admin.errors.editFailed'), life: 4000 })
    }
  } catch (e) {
    console.error("Errore di modifica utente:", e)
    toast.add({ severity: 'error', summary: t('common.error'), detail: t('admin.errors.connectionFailed'), life: 3000 })
  }
}

function confirmEdit(user) {
  confirm.require({
    message: t('admin.confirmEditMessage', { email: user.email }),
    header: t('admin.confirmEditHeader'),
    icon: 'pi pi-exclamation-triangle',
    acceptLabel: t('common.save'),
    rejectLabel: t('common.cancel'),
    acceptProps: { severity: 'primary', label: t('common.save') },
    rejectProps: { severity: 'secondary', outlined: true },
    accept: () => { saveEdit(user) }
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
      <h1 class="text-4xl font-extrabold text-900 mb-2">{{ t('admin.title') }}</h1>
      <p class="text-600 text-lg">{{ t('admin.subtitle') }}</p>
    </div>

    <!-- Main Card -->
    <div class="card p-4 shadow-3 border-round-xl surface-card">
      
      <!-- Toolbar/Search -->
      <div class="flex flex-column sm:flex-row justify-content-between align-items-center gap-3 mb-4">
        <span class="p-input-icon-left w-full sm:w-20rem">
          <i class="pi pi-search" />
          <InputText 
            v-model="searchQuery" 
            :placeholder="t('admin.searchPlaceholder')" 
            class="w-full border-round-lg pl-5" 
          />
        </span>
        <Button 
          icon="pi pi-refresh" 
          :label="t('admin.refresh')" 
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
        :currentPageReportTemplate="t('admin.pageReport', { first: '{first}', last: '{last}', totalRecords: '{totalRecords}' })"
      >
        <template #empty>
          <div class="text-center py-4 text-500">{{ t('admin.noUsers') }}</div>
        </template>

        <!-- Email -->
        <Column field="email" :header="t('admin.email')" sortable class="font-medium text-800">
          <template #body="slotProps">
            <div class="flex align-items-center">
              <span>{{ slotProps.data.email || 'N/A' }}</span>
              <span v-if="slotProps.data.auth0_id === currentUserId" class="ml-2 px-2 py-1 text-xs border-round bg-blue-100 text-blue-800 font-semibold">
                {{ t('admin.you') }}
              </span>
            </div>
          </template>
        </Column>

        <!-- Nome e Cognome -->
        <Column :header="t('admin.nameSurname')" sortable field="last_name">
          <template #body="slotProps">
            <template v-if="editingUserId === slotProps.data.id">
              <div class="flex flex-column gap-1">
                <InputText v-model="editForm.first_name" :placeholder="t('admin.firstName')" class="w-full" size="small" />
                <InputText v-model="editForm.last_name" :placeholder="t('admin.lastName')" class="w-full" size="small" />
              </div>
            </template>
            <template v-else>
              {{ slotProps.data.first_name || '' }} {{ slotProps.data.last_name || '' }}
              <span v-if="!slotProps.data.first_name && !slotProps.data.last_name" class="text-400 italic">{{ t('admin.profileNotComplete') }}</span>
            </template>
          </template>
        </Column>

        <!-- Telefono -->
        <Column field="phone" :header="t('admin.phone')">
          <template #body="slotProps">
            <template v-if="editingUserId === slotProps.data.id">
              <InputText v-model="editForm.phone" :placeholder="t('admin.phone')" class="w-full" size="small" />
            </template>
            <template v-else>
              {{ slotProps.data.phone || '-' }}
            </template>
          </template>
        </Column>

        <!-- Ruolo ed Edit -->
        <Column field="role" :header="t('admin.role')" sortable class="min-w-20rem">
          <template #body="slotProps">
            <div class="flex align-items-center gap-2">
              <Select 
                v-model="slotProps.data.role" 
                :options="roleOptions" 
                optionLabel="label" 
                optionValue="value"
                :placeholder="t('admin.selectRole')"
                class="w-full border-round-lg"
                :disabled="updatingUserId === slotProps.data.id || slotProps.data.auth0_id === currentUserId"
              />
              
              <template v-if="slotProps.data.role !== slotProps.data.originalRole && updatingUserId !== slotProps.data.id">
                <Button 
                  icon="pi pi-check" 
                  severity="success" 
                  class="p-button-rounded p-button-sm shadow-1" 
                  :title="t('admin.saveChanges')" 
                  @click="confirmSave(slotProps.data)" 
                />
                <Button 
                  icon="pi pi-times" 
                  severity="secondary" 
                  class="p-button-rounded p-button-sm p-button-text" 
                  :title="t('admin.cancelChanges')" 
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

        <!-- Azioni Edit -->
        <Column :header="t('common.actions')" class="w-10rem">
          <template #body="slotProps">
            <template v-if="editingUserId === slotProps.data.id">
              <div class="flex gap-2">
                <Button icon="pi pi-check" severity="success" rounded size="small" :title="t('common.save')" @click="confirmEdit(slotProps.data)" />
                <Button icon="pi pi-times" severity="secondary" rounded outlined size="small" :title="t('common.cancel')" @click="cancelEdit()" />
              </div>
            </template>
            <template v-else>
              <Button icon="pi pi-pencil" severity="info" rounded outlined size="small" :title="t('admin.editUser')" @click="startEdit(slotProps.data)" />
            </template>
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