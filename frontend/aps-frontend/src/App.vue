<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import Button from 'primevue/button'

const { isAuthenticated, isLoading, getAccessTokenSilently, logout } = useAuth0()

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
  <div v-if="isLoading" class="flex align-items-center justify-content-center min-h-screen">
    <i class="pi pi-spin pi-spinner text-3xl text-primary"></i>
  </div>
  
  <div v-else class="app-layout">
    <!-- Navbar globale visibile solo ad utente autenticato -->
    <header v-if="isAuthenticated" class="navbar py-3 px-4 border-bottom-1 border-light flex justify-content-between align-items-center surface-card shadow-1">
      <div class="flex align-items-center gap-3">
        <router-link to="/" class="font-bold text-lg text-color no-underline mr-3">Salvaiciclisti Roma</router-link>
        <nav class="flex gap-2">
          <router-link to="/" class="nav-link text-color-secondary no-underline font-medium text-sm">Home</router-link>
          <router-link to="/wizard" class="nav-link text-color-secondary no-underline font-medium text-sm">Iscrizione</router-link>
          <router-link v-if="isAdminOrTreasurer" to="/dashboard" class="nav-link text-color-secondary no-underline font-medium text-sm">Dashboard</router-link>
        </nav>
      </div>
      <div>
        <Button label="Logout" icon="pi pi-sign-out" severity="danger" size="small" outlined @click="doLogout" />
      </div>
    </header>

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
