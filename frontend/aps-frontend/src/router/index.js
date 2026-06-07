import { useAuth0 } from '@auth0/auth0-vue'
import { createRouter, createWebHistory } from 'vue-router'

import Home from '../pages/Home.vue'
import Wizard from '../pages/Wizard.vue'
import Dashboard from '../pages/Dashboard.vue'

const routes = [
  {
    path: '/',
    component : Home,
    // redirect: '/home',
    meta: { requiresAuth: false}
       // ✅ IMPORTANTISSIMO
  },
  {
    path: '/wizard',
    component: Wizard,
    meta: { requiresAuth: true}
  },
  {
    path: '/dashboard',
    component: Dashboard,
    meta: { requiresAuth: true, requiresAdmin: true }

  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})


router.beforeEach(async (to, from, next) => {

  const { isAuthenticated, loginWithRedirect } = useAuth0()

  // ✅ richiede login
  if (to.meta.requiresAuth && !isAuthenticated.value) {
    await loginWithRedirect({
      appState: { target: to.fullPath }
    })
    return
  }

  next()
})


export default router