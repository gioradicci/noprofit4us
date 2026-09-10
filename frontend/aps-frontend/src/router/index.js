import { createRouter, createWebHistory } from 'vue-router'
import { supabase } from '../supabase'
import { useUser } from '../composables/useUser'

import Home from '../pages/Home.vue'
import Wizard from '../pages/Wizard.vue'
import Dashboard from '../pages/Dashboard.vue'
import Gadgets from '../pages/Gadgets.vue'
import GadgetStock from '../pages/GadgetStock.vue'
import Warehouses from '../pages/Warehouses.vue'
import Admin from '../pages/Admin.vue'

const routes = [
  {
    path: '/',
    component: Home,
    meta: { requiresAuth: false }
  },
  {
    path: '/wizard',
    component: Wizard,
    meta: { requiresAuth: true }
  },
  {
    path: '/dashboard',
    component: Dashboard,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/gadgets',
    component: Gadgets,
    meta: { requiresAuth: true }
  },
  {
    path: '/gadget-stock',
    component: GadgetStock,
    meta: { requiresAuth: true }
  },
  {
    path: '/warehouses',
    component: Warehouses,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin',
    component: Admin,
    meta: { requiresAuth: true, requiresStrictAdmin: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const { user, isAuthenticated, fetchUser } = useUser()
  const { data: { session } } = await supabase.auth.getSession()
  const hasSession = !!session

  // ✅ richiede login
  if (to.meta.requiresAuth && !hasSession) {
    return '/'
  }

  const requiresAdmin = to.meta.requiresAdmin
  const requiresStrictAdmin = to.meta.requiresStrictAdmin
  const isGadgetRoute = ['/gadgets', '/gadget-stock', '/warehouses'].includes(to.path)

  if (hasSession && (requiresAdmin || requiresStrictAdmin || isGadgetRoute)) {
    try {
      const currentUser = await fetchUser()
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

      if (['/gadget-stock', '/warehouses'].includes(to.path)) {
        if (canManageGadgets) {
          return true
        } else {
          return '/'
        }
      }

      if (to.path === '/gadgets') {
        if (canManageGadgets || currentUser.status !== 'INCOMPLETE') {
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