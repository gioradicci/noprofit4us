<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import Button from 'primevue/button'
import Select from 'primevue/select'


const { isAuthenticated, isLoading, getAccessTokenSilently, loginWithRedirect } = useAuth0()

// ✅ Utente caricato dal backend
const backendUser = ref(null)
const loadingBackend = ref(false)

// ✅ Carica dettagli utente
async function loadUser() {
  if (!isAuthenticated.value) return
  loadingBackend.value = true
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
    console.error("Errore loadUser:", e)
  } finally {
    loadingBackend.value = false
  }
}

// ✅ Formatta data in formato italiano
function formatDate(dateStr) {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch (e) {
    return dateStr
  }
}

//  Monitora l'autenticazione Auth0
watch(isAuthenticated, (newVal) => {
  if (newVal) {
    loadUser()
  }
  
})

onMounted(() => {
  if (isAuthenticated.value) {
    loadUser()
  }
})
const memberTypes = ref([
  { label: "Socio Ordinario (10€)", value: "ORDINARIO" },
  { label: "Socio Sostenitore (30€)", value: "SOSTENITORE" }
])
const selectedMemberType = ref(null)

const paymentMethods = ref([
  { label: "Bonifico Bancario", value: "Bonifico Bancario" },
  { label: "PayPal", value: "PayPal" },
  { label: "Satispay", value: "Satispay" },
  { label: "Contanti", value: "Contanti" },
  { label: "POS negli eventi", value: "POS" }
])
const selectedPaymentMethod = ref(null)
const renewing = ref(false)

async function requestRenewal() {
  if (!selectedPaymentMethod.value || !selectedMemberType.value) return;
  renewing.value = true;
  try {
    const token = await getAccessTokenSilently()
    const res = await fetch("http://localhost:8000/users/me/request-renew", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ payment_method: selectedPaymentMethod.value, member_type: selectedMemberType.value })
    })
    if (res.ok) {
      await loadUser()
    }
  } catch (e) {
    console.error("Errore requestRenewal:", e)
  } finally {
    renewing.value = false;
  }
}

function memberNoActive() {
  //da Nov è possibile rifare la tessera, quindi indichiamo al socio che mancano due mesi
  //alla scadenza e cambiamo lo stile della tessera virtuale. Ad esempio se oggi è 10/11/2026
  //si può rifare la tessera per il 2027, quindi consideriamo il socio come non attivo
  let retVal =  (!backendUser.value.end_date || new Date(backendUser.value.end_date) < new Date() ) || (backendUser.value.is_renewal_pending)
  console.log(backendUser.value)
  
  return retVal
};

function getRoleIcon() {
  const role = backendUser.value?.role || 'USER';
  const roles = backendUser.value?.roles || [];
  
  if (role === 'ADMIN' || roles.includes('ADMIN')) return 'pi-crown';
  if (role === 'TREASURER' || roles.includes('TREASURER')) return 'pi-money-bill';
  return 'pi-user';
}

</script>

<template>
  <!-- ⏳ Stato Caricamento -->
  <div v-if="isLoading || (isAuthenticated && loadingBackend)" class="flex flex-column align-items-center justify-content-center min-h-30rem gap-3">
    <i class="pi pi-spin pi-spinner text-4xl text-primary"></i>
    <span class="text-color-secondary text-sm">Caricamento in corso...</span>
  </div>

  <div v-else class="home-container py-5 px-2">
    

    <!-- 🟢 CASO 1: UTENTE NON LOGGATO (Landing Page Pubblica) -->
    <div v-if="!isAuthenticated">
      
      <!-- Hero Banner -->
      <div class="hero-section text-center py-4 px-4 mb-5 border-round-3xl shadow-1 relative overflow-hidden">
        <div class="mb-3 " >
          <Image src="/logosic_roma.svg" alt="Logo" width="100" ></Image>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold mb-3 mt-0 text-primary-gradient">Associazione SalvaiciclistiRoma.it</h1>
        <p class="text-lg md:text-xl text-color-secondary mb-5 max-w-30rem mx-auto line-height-3">
          Entra a far parte della nostra comunità. Compila il modulo digitale e sostieni i nostri progetti di promozione sociale.
        </p>
        <Button label="Registrati / Accedi"  severity="info"  icon="pi pi-user-plus" size="large" class="p-button-raised p-button-lg" @click="loginWithRedirect" />
      </div>

      <!-- Sezione Come Funziona -->
      <div class="mb-6" >
        <h2 class="text-2xl md:text-3xl font-bold text-center mb-5">Come funziona l'iscrizione</h2>
        
        <div class="grid row-gap-4 column-gap-3 justify-content-center">
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">01</span>
              <h3 class="font-semibold text-base mb-2">Accesso & Profilo</h3>
              <p class="text-sm text-color-secondary m-0">Accedi con Google o registrati per creare la tua area riservata.</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">02</span>
              <h3 class="font-semibold text-base mb-2">Dati & Documento</h3>
              <p class="text-sm text-color-secondary m-0">Compila l'anagrafica nel wizard, inserendo dati personali e documento valido.</p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="step-card p-2 border-round-xl border-1 border-light surface-card text-left h-full">
              <span class="step-num text-3xl font-bold text-primary opacity-50 block mb-3">03</span>
              <h3 class="font-semibold text-base mb-2">Quota & Conferma</h3>
              <p class="text-sm text-color-secondary m-0">Paga la quota con i metodi di pagamento previsti e indica l'importo e metodo di pagamento nella richiesta. Validità per 12 mesi.</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Sezione Vantaggi -->
      <div>
        <h2 class="text-2xl md:text-3xl font-bold text-center mb-5">I vantaggi per i nostri soci</h2>
        <div class="grid row-gap-3 column-gap-3 justify-content-center">
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-compass text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">Accesso Risorse</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">
                Ottieni accesso immediato a tutti gli strumenti, materiali didattici e servizi messi a disposizione dall'associazione.
              </p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-users text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">Community Attiva</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">
                Partecipa ad eventi, assemblee ed attività sociali di gruppo insieme ad altri appassionati.
              </p>
            </div>
          </div>
          <div class="col-12 md:col-3">
            <div class="benefit-card p-4 border-round-xl border-1 border-light surface-card h-full text-left shadow-1">
              <i class="pi pi-heart text-3xl text-primary mb-3 block"></i>
              <h3 class="font-bold text-lg mb-2">Sostegno Sociale</h3>
              <p class="text-sm text-color-secondary m-0 leading-relaxed">
                Partecipa attivamente proponendo iniziative e regalandoci il tuo supporto per progetti di volontariato sul territorio.
              </p>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- 🟡 CASO 2: UTENTE LOGGATO CON STATO "INCOMPLETE" -->
    <div v-else-if="backendUser?.status === 'INCOMPLETE'" class="flex justify-content-center py-5">
      <div class="card p-5 text-center shadow-3 border-round-xl border-top-3 border-warning max-w-30rem surface-card">
        <i class="pi pi-user-plus text-5xl text-warning mb-3 block"></i>
        <h2 class="text-2xl font-bold mb-2">Profilo da completare</h2>
        <p class="text-color-secondary mb-4 line-height-3">
          Benvenuto! Per inoltrare la tua candidatura ed ottenere la tessera socio, devi completare i passaggi del modulo di iscrizione.
        </p>
        <router-link to="/wizard">
          <Button label="Inizia l'iscrizione" icon="pi pi-arrow-right" iconPos="right" size="large" class="w-full" />
        </router-link>
      </div>
    </div>

    <!-- 🔵 CASO 3: UTENTE LOGGATO CON STATO "PENDING" -->
    <div v-else-if="backendUser?.status === 'PENDING'" class="flex justify-content-center py-5">
      <div class="card p-5 text-center shadow-3 border-round-xl border-top-3 border-info max-w-30rem surface-card">
        <i class="pi pi-hourglass text-5xl text-info mb-3 block"></i>
        <h2 class="text-2xl font-bold mb-2">Richiesta in elaborazione</h2>
        <p class="text-color-secondary mb-3">
          Grazie per aver inviato la tua richiesta, <strong>{{ backendUser.first_name }}</strong>!
        </p>
        <p class="text-color-secondary mb-4 text-sm line-height-3">
          La tua iscrizione è in attesa di verifica del pagamento e dell'approvazione formale da parte del consiglio direttivo. Riceverai una mail di notifica ad approvazione completata.
        </p>
        
        <div class="surface-ground p-3 border-round text-left mb-4 border-1 border-light">
          <div class="flex justify-content-between py-2 border-bottom-1 border-light">
            <span class="text-xs text-color-secondary font-medium uppercase">Metodo scelto:</span>
            <span class="font-semibold text-xs">{{ backendUser.payment_method }}</span>
          </div>
          <div class="flex justify-content-between py-2">
            <span class="text-xs text-color-secondary font-medium uppercase">Stato:</span>
            <span class="font-semibold text-xs text-info uppercase">In Verifica</span>
          </div>
        </div>

        <router-link to="/wizard">
          <Button label="Modifica dati anagrafici" icon="pi pi-pencil" severity="secondary" outlined class="w-full" />
        </router-link>
      </div>
    </div>

    <!-- 🏆 CASO 4: UTENTE APPROVATO (Socio Attivo con Tessera) -->
    <div v-else-if="backendUser?.status === 'APPROVED'" class="flex flex-column align-items-center py-4">
      
      <div class="max-w-28rem w-full">
        <!-- Tessera Socio Digitale (Premium Glassmorphism Effect) -->
        <div class="p-4 text-white border-round-2xl shadow-4 relative overflow-hidden mb-4"
          :class="[ memberNoActive() ? 'membership-card_inactive' : 'membership-card' ]"
        >
          <div class="card-glow"></div>
          
          <div class="flex justify-content-between align-items-center mb-5">
            <div class="flex align-items-center gap-2">
              <i :class="['pi', getRoleIcon(), 'text-2xl']"></i>
              <span class="font-bold tracking-wider text-xs uppercase">Tessera Socio SalvaiciclistiRoma</span>
            </div>
            <span v-if="memberNoActive()" class="bg-blue-500 text-white text-xxs px-2.5 py-1 font-bold border-round-lg uppercase shadow-1">Socio non attivo</span>
            <span v-else class="bg-blue-500 text-white text-xxs px-2.5 py-1 font-bold border-round-lg uppercase shadow-1">Socio attivo</span>
            
          </div>

          <div class="mb-5">
            <h3 class="text-2xl font-bold m-0 letter-spacing-1" style="color: black !important;">{{ backendUser.first_name }} {{ backendUser.last_name }}</h3>
            <p class="text-xxs text-white-alpha-70 m-0 mt-1 uppercase font-semibold">Socio {{ backendUser.member_type || 'Ordinario' }}</p>
          </div>

          <div class="flex justify-content-between border-top-1 border-white-alpha-20 pt-3">
            <div class="flex flex-column text-left">
              <span class="text-xxs text-white-alpha-50 uppercase">Tessera N.</span>
              <span class="text-lg font-bold text-white">{{ backendUser.membership_number }}</span>
            </div>
            <div class="flex flex-column text-right">
              <span class="text-xxs text-white-alpha-50 uppercase">Valida fino al</span>
              <span class="text-lg font-bold text-white">{{ formatDate(backendUser.end_date) }}</span>
            </div>
          </div>
        </div>
        <!-- PENDING RENEWAL STATE -->
        <div class="mb-5">
          <div v-if="backendUser.is_renewal_pending" class="card p-4 shadow-2 border-round-xl surface-card text-center mt-4 border-top-3 border-info">
            <i class="pi pi-hourglass text-4xl text-info mb-3 block"></i>
            <h4 class="font-bold text-lg mb-2">Richiesta di rinnovo in elaborazione</h4>
            <p class="text-sm text-color-secondary m-0">La tua richiesta di rinnovo è in attesa di verifica del pagamento da parte del tesoriere.</p>
          </div>


          <!-- RENEW REQUEST FORM -->
          <div v-else-if="!backendUser.end_date || new Date(backendUser.end_date) < new Date()" class="card p-4 shadow-2 border-round-xl surface-card text-left mt-4 border-top-3 border-orange-500">
            <h4 class="font-bold text-base mb-3 text-color uppercase tracking-wide">Rinnova la tua iscrizione</h4>
            <p class="text-sm text-color-secondary mb-3">La tua iscrizione è scaduta o in scadenza. Scegli il metodo di pagamento e richiedi il rinnovo.</p>
            <div class="flex flex-column gap-3">
              <div class="flex flex-column gap-2">
                <label for="memberType" class="font-semibold text-sm">Tipo di Quota *</label>
                <Select id="memberType" v-model="selectedMemberType" :options="memberTypes" optionLabel="label" optionValue="value" placeholder="Seleziona la quota" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="paymentMethod" class="font-semibold text-sm">Metodo di Pagamento *</label>
                <Select id="paymentMethod" v-model="selectedPaymentMethod" :options="paymentMethods" optionLabel="label" optionValue="value" placeholder="Seleziona un metodo" class="w-full" />
              </div>
              <Button label="Richiedi Rinnovo" icon="pi pi-refresh" :loading="renewing" @click="requestRenewal" severity="warning" class="w-full mt-2" :disabled="!selectedPaymentMethod || !selectedMemberType" />
            </div>
          </div>
        </div>
        <!-- Box Riepilogo Dati Iscrizione -->
        <div class="card p-4 shadow-2 border-round-xl surface-card text-left">
          <h4 class="font-bold text-base mb-3 text-color uppercase tracking-wide">Dettagli Iscrizione</h4>
          
          <div class="flex flex-column gap-3">
            <div class="flex align-items-center gap-3">
              <i class="pi pi-calendar text-primary text-lg"></i>
              <div>
                <p class="text-xxs text-color-secondary m-0 uppercase font-semibold">Data Emissione</p>
                <p class="text-sm font-semibold m-0 text-color">{{ formatDate(backendUser.start_date) }}</p>
              </div>
            </div>
            <div class="flex align-items-center gap-3">
              <i class="pi pi-wallet text-primary text-lg"></i>
              <div>
                <p class="text-xxs text-color-secondary m-0 uppercase font-semibold">Metodo Pagamento</p>
                <p class="text-sm font-semibold m-0 text-color">{{ backendUser.payment_method }}</p>
              </div>
            </div>
            <div class="flex align-items-center gap-3">
              <i class="pi pi-id-card text-primary text-lg"></i>
              <div>
                <p class="text-xxs text-color-secondary m-0 uppercase font-semibold">Codice Fiscale</p>
                <p class="text-sm font-semibold m-0 text-color uppercase">{{ backendUser.tax_code }}</p>
              </div>
            </div>
          </div>

          <div class="mt-4 pt-3 border-top-1 border-light flex justify-content-between align-items-center">
            <span class="text-xs text-color-secondary">Hai bisogno di aggiornare i tuoi dati?</span>
            <router-link to="/wizard">
              <Button label="Modifica dati" icon="pi pi-pencil" size="small" severity="secondary" outlined />
            </router-link>
          </div>
        </div>



      </div>

    </div>

  </div>
</template>

<style scoped>
.home-container {
  max-width: 1020px;
  margin: 0 auto;
}

.hero-section {
  background: linear-gradient(135deg, rgba(59, 154, 255, 0.04) 0%, rgba(79, 195, 247, 0.04) 100%);
  border: 1px solid var(--border);
}

.text-primary-gradient {
 background: #ef7b14;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.benefit-card, .step-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  border-color: var(--border) !important;
}

.benefit-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow);
}

/* 🏆 Premium Membership Card CSS */
.membership-card {
  background: linear-gradient(0deg, #ec8e5b 20%,  #ea580c 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.membership-card_pending {
  background: linear-gradient(90deg, #ea580c 20%,  #5c5a59 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.membership-card_inactive {
  background: linear-gradient(0deg, #adaba9 20%,  #5c5a59 100%);
  border-radius: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 15px 30px rgba(124, 58, 237, 0.25);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-glow {
  position: absolute;
  top: -50%;
  left: -30%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.18) 0%, rgba(255, 255, 255, 0) 70%);
  transform: rotate(-30deg);
  pointer-events: none;
}

.text-xxs {
  font-size: 0.65rem;
  letter-spacing: 1.2px;
}

.border-light {
  border-color: var(--border) !important;
}

.surface-ground {
  background-color: var(--code-bg);
}

.text-muted {
  color: var(--text);
}
</style>
