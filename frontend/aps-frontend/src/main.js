
//  TEMA PRIMEVUE
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import 'primeicons/primeicons.css'
import 'primeflex/primeflex.css'

import router from './router'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext';
import Card from 'primevue/card';
import FloatLabel from 'primevue/floatlabel';
import Dropdown from 'primevue/dropdown';


import { createApp } from 'vue'
import App from './App.vue'
import './style.css'

import { createAuth0 } from '@auth0/auth0-vue'

const app = createApp(App)

app.component('DataTable', DataTable)
app.component('Column', Column)
app.component('Button', Button)
app.component('InputText', InputText)
app.component('Card', Card)
app.component('FloatLabel',FloatLabel)
app.component('Dropdown', Dropdown)

app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura
  }
})

app.use(
  createAuth0({
    domain: import.meta.env.VITE_AUTH0_DOMAIN,
    clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
    authorizationParams: {
      redirect_uri: window.location.origin,
      audience: "https://aps-api",
      scope: "openid profile email read:users"
    }
  })
)

app.mount('#app')
