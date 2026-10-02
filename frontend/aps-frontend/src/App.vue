<script setup>
import { API_URL } from './config.js'
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import Badge from 'primevue/badge'
import Menubar from 'primevue/menubar'
import Dialog from 'primevue/dialog'
import ManualeUtente from './pages/manuale_utente.md'
import { useI18n } from 'vue-i18n'
import { useUser } from './composables/useUser'

const { t, locale } = useI18n()
const {
  user: backendUser,
  isAuthenticated,
  isLoading,
  isAdminOrTreasurer,
  canManageGadgets,
  canViewGadgets,
  userInitials,
  userRole,
  initAuth,
  logout: doLogout
} = useUser()
const showManual = ref(false)

function changeLanguage(lang) {
  locale.value = lang
  localStorage.setItem('lang', lang)
}

const items = computed(() => {
  const menu = [
    { label: t('nav.home'), icon: 'pi pi-home', route: '/' },
    { label: t('nav.profile'), icon: 'pi pi-id-card', route: '/wizard' }
  ]

  if (isAdminOrTreasurer.value) {
    menu.push({ label: t('nav.dashboard'), icon: 'pi pi-chart-bar', route: '/dashboard' })
  }

  if (backendUser.value?.role === 'ADMIN') {
    menu.push({ label: t('nav.admin'), icon: 'pi pi-cog', route: '/admin' })
  }

  if (canManageGadgets.value) {
    menu.push({
      label: t('nav.gadgetManagement'),
      icon: 'pi pi-box',
      items: [
        { label: t('nav.gadgetList'), icon: 'pi pi-box', route: '/gadgets' },
        { label: t('nav.gadgetStock'), icon: 'pi pi-warehouse', route: '/gadget-stock' },
        { label: t('nav.warehouses'), icon: 'pi pi-building', route: '/warehouses' }
      ]
    })
  } else if (canViewGadgets.value) {
    menu.push({ label: t('nav.gadgets'), icon: 'pi pi-box', route: '/gadgets' })
  }

  return menu
})

onMounted(async () => {
  fetch(API_URL + "/wakeup").catch(e => console.log("Wakeup ping failed:", e))
  await initAuth()
})
</script>

<template>
<Toast position="top-center" />
<ConfirmDialog />

<div v-if="isLoading" class="flex align-items-center justify-content-center min-h-screen">
  <i class="pi pi-spin pi-spinner text-3xl text-primary"></i>
</div>

<div v-else class="app-layout">
  <Menubar :model="isAuthenticated ? items : []" class="py-2 px-2 sm:px-4 border-none border-bottom-1 border-light border-round-none shadow-1 mb-0">
    <template #start>
      <router-link to="/" class="mr-2 sm:mr-4 flex align-items-center">
        <Image src="/logosic_roma.bmp" alt="Logo" width="40" />
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
      <div class="flex align-items-center gap-1 sm:gap-2 flex-shrink-0">
        <Button icon="pi pi-book" class="p-button-text p-ml-2" @click="showManual = true" />
        <div class="flex gap-1 mr-1 sm:mr-3 border-round p-1 flex-shrink-0" style="background-color: var(--code-bg); border: 1px solid var(--border);">
          <Button 
            label="IT" 
            :severity="locale === 'it' ? 'primary' : 'secondary'" 
            size="small" 
            text 
            class="p-1 px-1 sm:px-2 text-xs font-bold min-w-0" 
            @click="changeLanguage('it')"
          />
          <Button 
            label="EN" 
            :severity="locale === 'en' ? 'primary' : 'secondary'" 
            size="small" 
            text 
            class="p-1 px-1 sm:px-2 text-xs font-bold min-w-0" 
            @click="changeLanguage('en')"
          />
        </div>

        <template v-if="isAuthenticated">
          <div v-if="backendUser" class="flex flex-column align-items-center justify-content-center mr-1 sm:mr-2 flex-shrink-0" style="line-height: 1;">
            <Avatar 
              :label="userInitials" 
              shape="circle" 
              style="background-color: #ea580c; color: #ffffff; width: 24px; height: 24px; font-size: 10px;" 
              class="font-bold flex-shrink-0" 
            />
            <span class="text-color-secondary font-semibold text-center" style="font-size: 8px; margin-top: 2px; white-space: nowrap; max-width: 65px; overflow: hidden; text-overflow: ellipsis;">
              {{ userRole }}
            </span>
          </div>
          <Button :title="t('nav.logout')" icon="pi pi-sign-out" severity="danger" size="small" outlined class="flex-shrink-0" @click="doLogout" />
        </template>
      </div>
    </template>
  </Menubar>

  <Dialog
    v-model:visible="showManual"
    modal
    scrollable
    maximizable
    :header="t('nav.manualTitle')"
    :style="{ width: '80vw', height: '80vh' }"
  >
    <div class="manual-body">
      <ManualeUtente />
    </div>
  </Dialog>

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

:deep(.p-menubar) {
  width: 100%;
  box-sizing: border-box;
}

:deep(.p-menubar-end) {
  margin-left: auto;
  min-width: 0;
}

/* Contenuto del manuale renderizzato da unplugin-vue-markdown */
.manual-body {
  text-align: left;
  padding: 0.25rem 0.75rem 1rem;
}

.manual-body :deep(h1) {
  font-size: 1.6rem;
  margin: 0.5rem 0 1rem;
  color: var(--text-h);
}

.manual-body :deep(h2) {
  font-size: 1.25rem;
  margin: 1.5rem 0 0.5rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--border);
  color: var(--text-h);
}

.manual-body :deep(h3) {
  font-size: 1.05rem;
  margin: 1.25rem 0 0.5rem;
  color: var(--text-h);
}

.manual-body :deep(h4) {
  font-size: 0.95rem;
  margin: 1rem 0 0.5rem;
  color: var(--text-h);
}

.manual-body :deep(p) {
  margin: 0.5rem 0;
  line-height: 1.6;
}

.manual-body :deep(ul),
.manual-body :deep(ol) {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.manual-body :deep(li) {
  margin: 0.2rem 0;
}

.manual-body :deep(code) {
  background: var(--code-bg);
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  font-family: var(--mono);
  font-size: 0.85em;
}

.manual-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0;
  font-size: 0.85rem;
}

.manual-body :deep(th),
.manual-body :deep(td) {
  border: 1px solid var(--border);
  padding: 0.4rem 0.6rem;
  text-align: left;
  vertical-align: top;
}

.manual-body :deep(th) {
  background: var(--code-bg);
  color: var(--text-h);
}

.manual-body :deep(blockquote) {
  margin: 0.75rem 0;
  padding: 0.5rem 0.85rem;
  border-left: 4px solid var(--accent-border);
  background: var(--accent-bg);
  border-radius: 0 6px 6px 0;
}

.manual-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}

.manual-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.25rem 0;
}

.manual-body :deep(a) {
  color: var(--accent);
}
</style>
