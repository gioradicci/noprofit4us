<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from './supabase'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Badge from 'primevue/badge'

const isAuthenticated = ref(false)
const isLoading = ref(true)

import Menubar from 'primevue/menubar'

const backendUser = ref(null)

async function loadBackendUser() {
  if (!isAuthenticated.value) return
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) return
    const token = session.access_token
    const res = await fetch("http://localhost:8000/users/me", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })
    if (res.ok) {
      backendUser.value = await res.json()
    }
  } catch (e) {
    console.error("Errore nel caricamento del ruolo da backend:", e)
  }
}

const isAdminOrTreasurer = computed(() => {
  const role = backendUser.value?.role
  return role === 'ADMIN' || role === 'TREASURER'
})

const userInitials = computed(() => {
  const first = backendUser.value?.first_name || ''
  const last = backendUser.value?.last_name || ''
  if (first && last) {
    return (first[0] + last[0]).toUpperCase()
  }
  return 'U'
})

const userRole = computed(() => {
  return backendUser.value?.role || ''
})

const roleBadgeSeverity = computed(() => {
  const role = backendUser.value?.role
  if (role === 'ADMIN') return 'contrast'
  if (role === 'TREASURER') return 'success'
  if (role === 'SECRETARY') return 'info'
  return 'secondary'
})

const canManageGadgets = computed(() => {
  const role = backendUser.value?.role
  const hasActiveMembership = backendUser.value?.has_active_membership
  const isRenewalPending = backendUser.value?.is_renewal_pending
  if (role === 'ADMIN') return true
  if (role === 'SECRETARY') {
    return !!hasActiveMembership && !isRenewalPending
  }
  return false
})

const items = computed(() => {
  const menu = [
    { label: 'Home', icon: 'pi pi-home', route: '/' },
    { label: 'Profilo', icon: 'pi pi-id-card', route: '/wizard' }
  ]
  if (isAdminOrTreasurer.value) {
    menu.push({ label: 'Dashboard', icon: 'pi pi-chart-bar', route: '/dashboard' })
  }
  if (backendUser.value?.role === 'ADMIN') {
    menu.push({ label: 'Admin', icon: 'pi pi-cog', route: '/admin' })
  }
  if (canManageGadgets.value) {
    menu.push({
      label: 'Gestione Gadget',
      icon: 'pi pi-box',
      items: [
        { label: 'Elenco Gadget', icon: 'pi pi-box', route: '/gadgets' },
        { label: 'Movimentazione gadget', icon: 'pi pi-warehouse', route: '/gadget-stock' },
        { label: 'Magazzini', icon: 'pi pi-building', route: '/warehouses' }
      ]
    })
  }
  return menu
})

onMounted(async () => {
  const { data: { session } } = await supabase.auth.getSession()
  isAuthenticated.value = !!session
  isLoading.value = false
  if (isAuthenticated.value) {
    loadBackendUser()
  }

  // Listen for auth changes
  supabase.auth.onAuthStateChange((event, _session) => {
    isAuthenticated.value = !!_session
    if (isAuthenticated.value) {
      loadBackendUser()
    } else {
      backendUser.value = null
    }
  })
})

async function doLogout() {
  await supabase.auth.signOut()
  window.location.href = '/'
}
</script>

<template>
  <Toast position="top-center" />
  <ConfirmDialog />
  <div v-if="isLoading" class="flex align-items-center justify-content-center min-h-screen">
    <i class="pi pi-spin pi-spinner text-3xl text-primary"></i>
  </div>
  
  <div v-else class="app-layout">
    <!-- Navbar globale visibile solo ad utente autenticato -->
    <Menubar v-if="isAuthenticated" :model="items" class="py-2 px-4 border-none border-bottom-1 border-light border-round-none shadow-1 mb-0">
      <template #start>
        <router-link to="/" class="mr-4 flex align-items-center">
          <Image src="/logo.svg" alt="Logo" width="50" />
        </router-link>
      </template>
      <template #item="{ item, props, hasSubmenu }">
        <router-link v-if="item.route" v-slot="{ href, navigate }" :to="item.route" custom>
            <a :href="href" v-bind="props.action" @click="navigate">
                <span :class="item.icon" />
                <span class="ml-2">{{ item.label }}</span>
            </a>
        </router-link>
        <a v-else :href="item.url" :target="item.target" v-bind="props.action">
            <span :class="item.icon" />
            <span class="ml-2">{{ item.label }}</span>
            <span v-if="hasSubmenu" class="pi pi-angle-down ml-auto" />
        </a>
      </template>
      <template #end>
        <div class="flex align-items-center gap-2">
          <div v-if="backendUser" class="flex align-items-center gap-2 mr-2">
            <Avatar :label="userInitials" shape="circle" style="background-color: #ea580c; color: #ffffff;" class="font-bold" />
            <div style="font-size: 9px;">{{ userRole }}</div>
          </div>
          <Button label="Logout" icon="pi pi-sign-out" severity="danger" size="small" outlined @click="doLogout" />
        </div>
      </template>
    </Menubar>

    <!-- ✅ CONTENUTO PAGINE -->
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.navbar {
  border-bottom: 1px solid var(--border);
}

.nav-link {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  transition: background-color 0.2s, color 0.2s;
}

.nav-link:hover {
  background-color: var(--code-bg);
  color: var(--text-h);
}

.router-link-active.nav-link {
  color: #ea580c;
  background-color: var(--accent-bg);
  font-weight: 600;
}

.content {
  flex-grow: 1;
}
</style>
