import { createRouter, createWebHistory } from 'vue-router'
import { supabase, isInitialRecoveryLink, checkUrlAuthError } from '../supabase'
import { useUser } from '../composables/useUser'

import Home from '../pages/Home.vue'

const routes = [
  {
    path: '/',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    component: () => import('../pages/ResetPassword.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/wizard',
    component: () => import('../pages/Wizard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    component: () => import('../pages/Dashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/gadgets',
    component: () => import('../pages/Gadgets.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/gadget-stock',
    component: () => import('../pages/GadgetStock.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/warehouses',
    component: () => import('../pages/Warehouses.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: () => import('../pages/Admin.vue'),
    meta: { requiresAuth: true, requiresStrictAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const { isPasswordRecovery, fetchUser } = useUser()

  // 🔑 CONTROLLA SUBITO LA RECOVERY PRIMA DI CHIAMARE getSession()
  const hasAuthError = !!checkUrlAuthError()
  const isRecoveryMode = !hasAuthError && isPasswordRecovery.value

  if (isRecoveryMode && to.path !== '/reset-password') {
    return '/reset-password'
  }

  // Identifica i requisiti della rotta
  const requiresAdmin = to.meta.requiresAdmin
  const requiresStrictAdmin = to.meta.requiresStrictAdmin
  const isProtectedGadgetRoute = ['/gadget-stock', '/warehouses'].includes(to.path)
  const isProtectedRoute = to.meta.requiresAuth || requiresAdmin || requiresStrictAdmin || isProtectedGadgetRoute

  // Se la rotta non è protetta (es. '/', '/gadgets', '/reset-password'), consenti la navigazione immediatamente
  if (!isProtectedRoute) {
    return true
  }

  const { data: { session } } = await supabase.auth.getSession()
  const hasSession = !!session

  // Se la rotta richiede autenticazione e non c'è sessione attiva, reindirizza alla home
  if (!hasSession) {
    return '/'
  }

  if (requiresAdmin || requiresStrictAdmin || isProtectedGadgetRoute) {
    try {
      const currentUser = await fetchUser(false, session)
      if (!currentUser) {
        return '/'
      }

      const role = currentUser.role
      const hasActiveMembership = currentUser.has_active_membership

      if (requiresStrictAdmin) {
        if (role === 'ADMIN') {
          return true
        } else {
          return '/'
        }
      }

      if (requiresAdmin) {
        if (role === 'ADMIN' || role === 'TREASURER') {
          return true
        } else {
          return '/'
        }
      }

      const isSecretary = role === 'SECRETARY' && hasActiveMembership && !currentUser.is_renewal_pending
      const canManageGadgets = role === 'ADMIN' || isSecretary

      if (isProtectedGadgetRoute) {
        if (canManageGadgets) {
          return true
        } else {
          return '/'
        }
      }
    } catch (e) {
      console.error("Router guard error:", e)
      return '/'
    }
  }

  return true
})

export default router