import { ref, computed } from 'vue'
import { supabase } from '../supabase'
import { API_URL } from '../config'

// Singleton reactive state shared across all components and router
const user = ref(null)
const isAuthenticated = ref(false)
const isLoading = ref(true)

let inFlightPromise = null
let authListenerInitialized = false

const isAdminOrTreasurer = computed(() => {
  const role = user.value?.role
  return role === 'ADMIN' || role === 'TREASURER'
})

const isAdmin = computed(() => {
  return user.value?.role === 'ADMIN'
})

const userInitials = computed(() => {
  const first = user.value?.first_name || ''
  const last = user.value?.last_name || ''
  if (first && last) {
    return (first[0] + last[0]).toUpperCase()
  }
  return 'U'
})

const userRole = computed(() => {
  return user.value?.role || ''
})

const canManageGadgets = computed(() => {
  const role = user.value?.role
  const hasActiveMembership = user.value?.has_active_membership
  const isRenewalPending = user.value?.is_renewal_pending
  if (role === 'ADMIN') return true
  if (role === 'SECRETARY') {
    return !!hasActiveMembership && !isRenewalPending
  }
  return false
})

async function fetchUser(force = false) {
  // If we already have the user and don't need a force refresh, return cached data
  if (user.value && !force) {
    return user.value
  }

  // Deduplicate concurrent requests
  if (inFlightPromise) {
    return inFlightPromise
  }

  inFlightPromise = (async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        isAuthenticated.value = false
        user.value = null
        return null
      }

      isAuthenticated.value = true
      const token = session.access_token
      const res = await fetch(API_URL + "/users/me", {
        headers: { Authorization: `Bearer ${token}` }
      })

      if (res.ok) {
        user.value = await res.json()
        return user.value
      } else if (res.status === 401 || res.status === 403) {
        user.value = null
        return null
      }
    } catch (e) {
      console.error("Errore nel caricamento utente da /users/me:", e)
      return null
    } finally {
      inFlightPromise = null
    }
  })()

  return inFlightPromise
}

async function initAuth() {
  if (authListenerInitialized) return

  try {
    const { data: { session } } = await supabase.auth.getSession()
    isAuthenticated.value = !!session
    if (isAuthenticated.value) {
      await fetchUser()
    }
  } finally {
    isLoading.value = false
  }

  supabase.auth.onAuthStateChange(async (event, session) => {
    isAuthenticated.value = !!session

    if (event === 'SIGNED_IN') {
      await fetchUser(true)
    } else if (event === 'SIGNED_OUT') {
      user.value = null
      isAuthenticated.value = false
    } else if (event === 'USER_UPDATED') {
      await fetchUser(true)
    } else if (event === 'INITIAL_SESSION') {
      if (session && !user.value) {
        await fetchUser()
      }
    }
    // Note: TOKEN_REFRESHED does NOT trigger a re-fetch of /users/me unless user is missing
    if (session && !user.value) {
      await fetchUser()
    }
  })

  authListenerInitialized = true
}

async function logout() {
  await supabase.auth.signOut()
  user.value = null
  isAuthenticated.value = false
  window.location.href = '/'
}

export function useUser() {
  return {
    user,
    isAuthenticated,
    isLoading,
    isAdmin,
    isAdminOrTreasurer,
    canManageGadgets,
    userInitials,
    userRole,
    fetchUser,
    initAuth,
    logout
  }
}
