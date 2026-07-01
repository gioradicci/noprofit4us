import { API_URL } from '../config.js'
import { createRouter, createWebHistory } from 'vue-router'
import { supabase } from '../supabase'

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

let cachedUser = null

router.beforeEach(async (to) => {
  const { data: { session } } = await supabase.auth.getSession()
  const isAuthenticated = !!session

  // ✅ richiede login
  if (to.meta.requiresAuth && !isAuthenticated) {
    cachedUser = null
    // Supabase non ha un loginWithRedirect nativo nello stesso modo di Auth0.
    // Redirigiamo alla home dove c'è la landing page e i bottoni di login.
    return '/'
  }

  if (!isAuthenticated) {
    cachedUser = null
  }

  const requiresAdmin = to.meta.requiresAdmin
  const requiresStrictAdmin = to.meta.requiresStrictAdmin
  const isGadgetRoute = ['/gadgets', '/gadget-stock', '/warehouses'].includes(to.path)

  if (isAuthenticated && (requiresAdmin || requiresStrictAdmin || isGadgetRoute)) {
    try {
      if (!cachedUser) {
        const token = session.access_token
        const res = await fetch(API_URL + "/users/me", {
          headers: {
            Authorization: `Bearer ${token}`
          }
        })
        if (res.ok) {
          cachedUser = await res.json()
        }
      }

      if (!cachedUser) {
        return '/'
      }

      const role = cachedUser.role
      const hasActiveMembership = cachedUser.has_active_membership

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

      if (isGadgetRoute) {
        if (role === 'ADMIN') {
          return true
        } else if (role === 'SECRETARY' && hasActiveMembership && !cachedUser.is_renewal_pending) {
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