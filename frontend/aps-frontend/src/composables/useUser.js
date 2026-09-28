import { ref, computed } from 'vue'
import { supabase, isInitialRecoveryLink, checkUrlAuthError, clearRecoveryLink } from '../supabase'
import { API_URL } from '../config'

// Singleton reactive state shared across all components and router
const user = ref(null)
const isAuthenticated = ref(false)
const isLoading = ref(true)
const isFetchingUser = ref(false)
const isPasswordRecovery = ref(
  !checkUrlAuthError() && (
    isInitialRecoveryLink || (
      typeof window !== 'undefined' && (
        window.location.href.includes('type=recovery') ||
        window.location.hash.includes('type=recovery') ||
        window.location.search.includes('type=recovery') ||
        (typeof sessionStorage !== 'undefined' && sessionStorage.getItem('is_password_recovery') === 'true')
      )
    )
  )
)

export function clearRecoveryState() {
  clearRecoveryLink()
  isPasswordRecovery.value = false
  try {
    sessionStorage.removeItem('is_password_recovery')
  } catch (e) {}
}

let inFlightPromise = null
let authListenerInitialized = false

// Helper per ottenere la sessione con timeout di sicurezza contro eventuali deadlock dei WebLocks di Supabase
export async function safeGetSession(timeoutMs = 4000) {
  try {
    const sessionPromise = supabase.auth.getSession()
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('getSession timeout')), timeoutMs)
    )
    const result = await Promise.race([sessionPromise, timeoutPromise])
    return result?.data?.session || null
  } catch (err) {
    console.warn('safeGetSession fallback o timeout:', err)
    return null
  }
}

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

const canViewGadgets = computed(() => {
  if (!user.value) return false
  if (canManageGadgets.value) return true
  return user.value.status !== 'INCOMPLETE'
})

async function fetchUser(force = false, providedSession = null) {
  // If we already have the user and don't need a force refresh, return cached data
  if (user.value && !force) {
    return user.value
  }

  // Deduplicate concurrent requests
  if (inFlightPromise) {
    return inFlightPromise
  }

  isFetchingUser.value = true
  inFlightPromise = (async () => {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 12000)

    try {
      const session = providedSession || (await safeGetSession())
      if (!session) {
        isAuthenticated.value = false
        user.value = null
        return null
      }

      isAuthenticated.value = true
      const token = session.access_token
      const res = await fetch(API_URL + "/users/me", {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal
      })

      if (res.ok) {
        user.value = await res.json()
        return user.value
      } else if (res.status === 401 || res.status === 403) {
        console.warn("Sessione o token non valido sul backend (401/403). Pulizia sessione locale...")
        user.value = null
        isAuthenticated.value = false
        try {
          await supabase.auth.signOut()
        } catch (signOutErr) {
          console.error("Errore signOut:", signOutErr)
        }
        return null
      } else {
        console.error("Errore risposta backend /users/me:", res.status)
        return null
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        console.warn("Timeout (12s) durante la chiamata a /users/me")
      } else {
        console.error("Errore nel caricamento utente da /users/me:", e)
      }
      return null
    } finally {
      clearTimeout(timeoutId)
      inFlightPromise = null
      isFetchingUser.value = false
    }
  })()

  return inFlightPromise
}

async function initAuth() {
  if (authListenerInitialized) return
  authListenerInitialized = true

  // Garantisce che isLoading non rimanga mai bloccato indefinitamente
  const safetyTimeout = setTimeout(() => {
    isLoading.value = false
  }, 3000)

  // Register listener before getting session to avoid missing initial auth events
  supabase.auth.onAuthStateChange((event, session) => {
    isAuthenticated.value = !!session

    if (event === 'PASSWORD_RECOVERY') {
      isPasswordRecovery.value = true
      try {
        sessionStorage.setItem('is_password_recovery', 'true')
      } catch (e) {}
      if (typeof window !== 'undefined' && window.location.pathname !== '/reset-password') {
        window.location.href = '/reset-password'
      }
    } else if (event === 'SIGNED_IN') {
      if (session) {
        setTimeout(() => fetchUser(true, session), 0)
      }
    } else if (event === 'SIGNED_OUT') {
      user.value = null
      isAuthenticated.value = false
      isPasswordRecovery.value = false
      try {
        sessionStorage.removeItem('is_password_recovery')
      } catch (e) {}
    } else if (event === 'USER_UPDATED') {
      if (session) {
        setTimeout(() => fetchUser(true, session), 0)
      }
    } else if (event === 'INITIAL_SESSION') {
      if (session && !user.value) {
        setTimeout(() => fetchUser(false, session), 0)
      }
    } else if (event === 'TOKEN_REFRESHED') {
      if (session && !user.value) {
        setTimeout(() => fetchUser(false, session), 0)
      }
    }
  })

  try {
    const session = await safeGetSession()
    isAuthenticated.value = !!session
    if (isAuthenticated.value && session) {
      await fetchUser(false, session)
    }
  } finally {
    clearTimeout(safetyTimeout)
    isLoading.value = false
  }
}

async function logout() {
  try {
    await supabase.auth.signOut()
  } catch (e) {
    console.error("Errore durante signOut:", e)
  }
  user.value = null
  isAuthenticated.value = false
  clearRecoveryState()
  window.location.href = '/'
}

export function useUser() {
  return {
    user,
    isAuthenticated,
    isLoading,
    isFetchingUser,
    isPasswordRecovery,
    clearRecoveryState,
    isAdmin,
    isAdminOrTreasurer,
    canManageGadgets,
    canViewGadgets,
    userInitials,
    userRole,
    fetchUser,
    initAuth,
    logout
  }
}
