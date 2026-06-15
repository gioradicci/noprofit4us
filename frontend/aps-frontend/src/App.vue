<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import Button from 'primevue/button'

const { isAuthenticated, isLoading, getAccessTokenSilently, logout } = useAuth0()

import Menubar from 'primevue/menubar'

const backendUser = ref(null)

async function loadBackendUser() {
  if (!isAuthenticated.value) return
  try {
    const token = await getAccessTokenSilently()
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

const items = computed(() => {
  const menu = [
    { label: 'Home', icon: 'pi pi-home', route: '/' },
    { label: 'Profilo', icon: 'pi pi-id-card', route: '/wizard' }
  ]
  if (isAdminOrTreasurer.value) {
    menu.push({ label: 'Dashboard', icon: 'pi pi-chart-bar', route: '/dashboard' })
  }
  return menu
})

watch(isAuthenticated, (newVal) => {
  if (newVal) {
    loadBackendUser()
  }
})

onMounted(() => {
  if (isAuthenticated.value) {
    loadBackendUser()
  }
})

function doLogout() {
  logout({ logoutParams: { returnTo: window.location.origin } })
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
        <Button label="Logout" icon="pi pi-sign-out" severity="danger" size="small" outlined @click="doLogout" />
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
