import { useAuth0 } from '@auth0/auth0-vue'
import { createRouter, createWebHistory } from 'vue-router'

import Home from '../pages/Home.vue'
import Wizard from '../pages/Wizard.vue'
import Dashboard from '../pages/Dashboard.vue'
import Gadgets from '../pages/Gadgets.vue'
import GadgetStock from '../pages/GadgetStock.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})


let cachedUser = null

router.beforeEach(async (to) => {

  const { isAuthenticated, getAccessTokenSilently, loginWithRedirect } = useAuth0()

  // ✅ richiede login
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    cachedUser = null
    await loginWithRedirect({
      appState: { target: to.fullPath }
    })
    return false
  }

  if (!isAuthenticated.value) {
    cachedUser = null
  }

  const requiresAdmin = to.meta.requiresAdmin
  const isGadgetRoute = ['/gadgets', '/gadget-stock'].includes(to.path)

  if (isAuthenticated.value && (requiresAdmin || isGadgetRoute)) {
    try {
      if (!cachedUser) {
        const token = await getAccessTokenSilently()
        const res = await fetch("http://localhost:8000/users/me", {
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
        } else if (role === 'SECRETARY' && hasActiveMembership) {
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