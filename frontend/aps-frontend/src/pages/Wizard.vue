<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuth0 } from '@auth0/auth0-vue'
import { useToast } from 'primevue/usetoast'

// Import PrimeVue Stepper and custom components
import Stepper from 'primevue/stepper'
import StepList from 'primevue/steplist'
import Step from 'primevue/step'
import StepPanels from 'primevue/steppanels'
import StepPanel from 'primevue/steppanel'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'

const { getAccessTokenSilently } = useAuth0()
const toast = useToast()

// ✅ Utente backend
const backendUser = ref(null)

const initialDate = new Date(new Date().getFullYear() -18, 0, 1);


const isSocioAttivo = computed(() => {
  if (!backendUser.value) return false;
  return backendUser.value.status === 'APPROVED' && backendUser.value.end_date && new Date(backendUser.value.end_date) >= new Date();
});

// ✅ Form di profilo
const profile = ref({
  first_name: "",
  last_name: "",
  tax_code: "",
  birth_date: null,
  birth_place: "",
  phone: "",
  address: "",
  city: "",
  zip_code: "",
  province: "",
  municipality: "",
  document_type: "",
  document_number: "",
  document_expiry: null,
  profession: "",
  usage_type: [],
  avg_km_per_day: null,
  member_type: "",
  payment_method: "",
  municipio_roma: ""
})

const usageTypes = ref([
  { label: "Casa/Lavoro", value: "casa-lavoro" },
  { label: "Viaggio", value: "viaggio" },
  { label: "Sport", value: "sport" },
  { label: "Accompagnare figli", value: "accompagnare figli" },
  { label: "Spesa", value: "spesa" },
  { label: "Strumento Lavoro", value: "strumento lavoro" }
])

// ✅ Opzioni per Select
const documentTypes = ref([
  { label: "Carta d'Identità", value: "Carta d'Identità" },
  { label: "Patente di Guida", value: "Patente di Guida" },
  { label: "Passaporto", value: "Passaporto" }
])

const paymentMethods = ref([
  { label: "Bonifico Bancario", value: "Bonifico Bancario" },
  { label: "PayPal", value: "PayPal" },
  { label: "Satispay", value: "Satispay" },
  { label: "Contanti", value: "Contanti" },
  { label: "POS negli eventi", value: "POS" }
])

const memberTypes = ref([
  { label: "Socio Ordinario (10€)", value: "ORDINARIO" },
  { label: "Socio Sostenitore (30€)", value: "SOSTENITORE" }
])

const municipiRoma = ref([
  { label: "I", value: "I" },
  { label: "II", value: "II" },
  { label: "III", value: "III" },
  { label: "IV", value: "IV" },
  { label: "V", value: "V" },
  { label: "VI", value: "VI" },
  { label: "VII", value: "VII" },
  { label: "VIII", value: "VIII" },
  { label: "IX", value: "IX" },
  { label: "X", value: "X" },
  { label: "XI", value: "XI" },
  { label: "XII", value: "XII" },
  { label: "XIII", value: "XIII" },
  { label: "XIV", value: "XIV" },
  { label: "XV", value: "XV" }
])

// ✅ Carica dati utente
async function loadUser() {
  try {
    const token = await getAccessTokenSilently()

    const res = await fetch("http://localhost:8000/users/me", {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    backendUser.value = await res.json()

    // Precompila form
    profile.value = {
      first_name: backendUser.value.first_name || "",
      last_name: backendUser.value.last_name || "",
      tax_code: backendUser.value.tax_code || "",
      birth_date: backendUser.value.birth_date ? new Date(backendUser.value.birth_date) : null,
      birth_place: backendUser.value.birth_place || "",
      phone: backendUser.value.phone || "",
      address: backendUser.value.address || "",
      city: backendUser.value.city || "",
      zip_code: backendUser.value.zip_code || "",
      province: backendUser.value.province || "",
      municipality: backendUser.value.municipality || "",
      document_type: backendUser.value.document_type || "",
      document_number: backendUser.value.document_number || "",
      document_expiry: backendUser.value.document_expiry ? new Date(backendUser.value.document_expiry) : null,
      profession: backendUser.value.profession || "",
      usage_type: backendUser.value.usage_type || [],
      avg_km_per_day: backendUser.value.avg_km_per_day || null,
      member_type: backendUser.value.member_type || "",
      payment_method: backendUser.value.payment_method || "",
      municipio_roma: backendUser.value.municipio_roma || ""
    }

  } catch (e) {
    console.error("Errore loadUser:", e)
  }
}

// ✅ Invia dati al backend
async function submit() {
  try {
    const token = await getAccessTokenSilently()

    // Formatta date prima dell'invio
    const payload = { ...profile.value }
    if (payload.birth_date) {
      payload.birth_date = payload.birth_date.toISOString().substring(0, 10)
    }
    if (payload.document_expiry) {
      payload.document_expiry = payload.document_expiry.toISOString().substring(0, 10)
    }

    const res = await fetch("http://localhost:8000/users/me", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(payload)
    })

    if (!res.ok) {
      throw new Error(`Errore salvataggio: ${res.status}`);
    }

    const data = await res.json()
    backendUser.value = data
    console.log("SAVED:", data)
    
    toast.add({ severity: 'success', summary: 'Successo', detail: 'Dati salvati correttamente', life: 3000 });

  } catch (e) {
    console.error("Errore submit:", e)
    toast.add({ severity: 'error',  summary: 'Errore', detail: 'Si è verificato un errore durante il salvataggio', life: 3000 });
  }
}

// ✅ Carica al montaggio
onMounted(() => {
  loadUser()
})
</script>

<template>
  <div class="wizard-container py-5 px-3">
    
    <!-- ✅ Messaggio stato iscrizione -->
    <div v-if="backendUser?.status === 'PENDING'" class="status-box mb-4 p-3 border-round flex align-items-center gap-2">
      <i class="pi pi-check-circle text-xl text-success"></i>
      <div>
        <strong class="block">Iscrizione completata</strong>
        <span class="text-sm">La tua richiesta è in attesa di approvazione da parte del direttivo.</span>
      </div>
    </div>

    <!-- ✅ Titolo della sezione -->
    <div class="text-center mb-5">
      <h2 class="font-bold text-3xl mb-2">
        {{ backendUser?.status === 'INCOMPLETE' ? 'Iscrizione Nuovo Socio' : 'Profilo Socio' }}
      </h2>
      <p class="text-muted text-sm">Inserisci tutti i dettagli richiesti per completare l'anagrafica soci</p>
    </div>

    <!-- ✅ Contenitore Stepper -->
    <div class="card p-4 shadow-2 border-round surface-card">
      <Stepper value="1">
        <StepList class="mb-4">
          <Step value="1">Anagrafica</Step>
          <Step value="2">Contatti</Step>
          <Step value="3">Documento</Step>
          <Step value="4">Profilo</Step>
          <Step value="5">Pagamento</Step>
          <Step value="6">Completa</Step>
        </StepList>

        <StepPanels>
          <!-- 1️⃣ STEP: Dati Anagrafici -->
          <StepPanel v-slot="{ activateCallback }" value="1">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="first_name" class="font-semibold text-sm">Nome *</label>
                <InputText id="first_name" v-model="profile.first_name" placeholder="Inserisci il tuo nome" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="last_name" class="font-semibold text-sm">Cognome *</label>
                <InputText id="last_name" v-model="profile.last_name" placeholder="Inserisci il tuo cognome" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="tax_code" class="font-semibold text-sm">Codice Fiscale *</label>
                <InputText id="tax_code" v-model="profile.tax_code" placeholder="Inserisci il codice fiscale" class="w-full uppercase" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="birth_date" class="font-semibold text-sm">Data di Nascita *</label>
                <DatePicker 
                  id="birth_date" 
                  v-model="profile.birth_date" 
                  dateFormat="dd/mm/yy" 
                  class="w-full" 
                  :pt="{
                    root: ({ state, props }) => {
                      if (!props.modelValue && state.currentYear === new Date().getFullYear()) {
                        state.currentYear = initialDate.getFullYear();
                        state.currentMonth = initialDate.getMonth();
                      }
                    }
                  }"
                />
              </div>
              <div class="flex flex-column gap-2">
                <label for="birth_place" class="font-semibold text-sm">Luogo di Nascita *</label>
                <InputText id="birth_place" v-model="profile.birth_place" placeholder="Città di nascita" class="w-full" />
              </div>
            </div>
            <div class="flex pt-4 justify-content-end border-top-1 border-light">
              <Button 
                label="Avanti" 
                icon="pi pi-arrow-right" 
                iconPos="right" 
                :disabled="!profile.first_name || !profile.last_name || !profile.tax_code || !profile.birth_date || !profile.birth_place" 
                @click="activateCallback('2')" 
              />
            </div>
          </StepPanel>

          <!-- 2️⃣ STEP: Contatti -->
          <StepPanel v-slot="{ activateCallback }" value="2">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="phone" class="font-semibold text-sm">Telefono *</label>
                <InputText id="phone" v-model="profile.phone" placeholder="Inserisci il numero di telefono" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="address" class="font-semibold text-sm">Indirizzo di Residenza *</label>
                <InputText id="address" v-model="profile.address" placeholder="Via e Numero Civico" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="city" class="font-semibold text-sm">Città *</label>
                <InputText id="city" v-model="profile.city" placeholder="Città" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="zip_code" class="font-semibold text-sm">CAP *</label>
                <InputText id="zip_code" v-model="profile.zip_code" placeholder="Codice Avviamento Postale" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="province" class="font-semibold text-sm">Provincia *</label>
                <InputText id="province" v-model="profile.province" placeholder="Sigla Provincia (es. RM)" class="w-full uppercase" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="municipality" class="font-semibold text-sm">Comune *</label>
                <InputText id="municipality" v-model="profile.municipality" placeholder="Comune" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="municipio_roma" class="font-semibold text-sm">Numero Municipio (I - XII) *</label>
                <Select 
                  id="municipio_roma" 
                  v-model="profile.municipio_roma" 
                  :options="municipiRoma" 
                  optionLabel="label" 
                  optionValue="value" 
                  placeholder="Seleziona il Municipio" 
                  class="w-full" 
                />
              </div>
            </div>
            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('1')" />
              <Button 
                label="Avanti" 
                icon="pi pi-arrow-right" 
                iconPos="right" 
                :disabled="!profile.phone || !profile.address || !profile.city || !profile.zip_code || !profile.province || !profile.municipality || !profile.municipio_roma" 
                @click="activateCallback('3')" 
              />
            </div>
          </StepPanel>

          <!-- 3️⃣ STEP: Documento -->
          <StepPanel v-slot="{ activateCallback }" value="3">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="document_type" class="font-semibold text-sm">Tipo Documento *</label>
                <Select 
                  id="document_type" 
                  v-model="profile.document_type" 
                  :options="documentTypes" 
                  optionLabel="label" 
                  optionValue="value" 
                  placeholder="Seleziona tipo documento" 
                  class="w-full" 
                />
              </div>
              <div class="flex flex-column gap-2">
                <label for="document_number" class="font-semibold text-sm">Numero Documento *</label>
                <InputText id="document_number" v-model="profile.document_number" placeholder="Inserisci il numero del documento" class="w-full uppercase" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="document_expiry" class="font-semibold text-sm">Scadenza Documento *</label>
                <DatePicker id="document_expiry" v-model="profile.document_expiry" dateFormat="dd/mm/yy" class="w-full" />
              </div>
            </div>
            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('2')" />
              <Button 
                label="Avanti" 
                icon="pi pi-arrow-right" 
                iconPos="right" 
                :disabled="!profile.document_type || !profile.document_number || !profile.document_expiry" 
                @click="activateCallback('4')" 
              />
            </div>
          </StepPanel>

          <!-- 4️⃣ STEP: Profilo Associativo -->
          <StepPanel v-slot="{ activateCallback }" value="4">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="profession" class="font-semibold text-sm">Professione</label>
                <InputText id="profession" v-model="profile.profession" placeholder="La tua professione" class="w-full" />
              </div>
              <div class="flex flex-column gap-2">
                <label for="usage_type" class="font-semibold text-sm">Tipo Uso</label>
                <MultiSelect 
                  id="usage_type" 
                  v-model="profile.usage_type" 
                  :options="usageTypes" 
                  optionLabel="label" 
                  optionValue="value" 
                  placeholder="Seleziona i tipi di uso" 
                  class="w-full" 
                  display="chip"
                />
              </div>
              <div class="flex flex-column gap-2">
                <label for="avg_km_per_day" class="font-semibold text-sm">Km media giorno</label>
                <InputNumber id="avg_km_per_day" v-model="profile.avg_km_per_day" placeholder="Km media giorno" class="w-full" />
              </div>
            </div>
            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('3')" />
              <Button 
                label="Avanti" 
                icon="pi pi-arrow-right" 
                iconPos="right" 
                @click="activateCallback('5')" 
              />
            </div>
          </StepPanel>

          <!-- 5️⃣ STEP: Pagamento -->
          <StepPanel v-slot="{ activateCallback }" value="5">
            <div class="flex flex-column gap-4 py-3 text-left">
              <div class="flex flex-column gap-2">
                <label for="member_type" class="font-semibold text-sm">Tipo di Quota *</label>
                <Select 
                  id="member_type" 
                  v-model="profile.member_type" 
                  :options="memberTypes" 
                  optionLabel="label" 
                  optionValue="value" 
                  placeholder="Seleziona la quota" 
                  class="w-full" 
                  :disabled="isSocioAttivo"
                />
              </div>

              <div class="flex flex-column gap-2 mt-3">
                <label for="payment_method" class="text-sm">Paga con bonifico, Satispay o Paypal. <a href="https://salvaiciclistiroma.it/lassociazione/diventa-socio/" target="_blank" >Qui trovi le coordinate.</a></label>
                <label for="payment_method" class="font-semibold text-sm mt-2">Metodo di Pagamento *</label>
                <Select 
                  id="payment_method" 
                  v-model="profile.payment_method" 
                  :options="paymentMethods" 
                  optionLabel="label" 
                  optionValue="value" 
                  placeholder="Seleziona il metodo di pagamento" 
                  class="w-full" 
                  :disabled="isSocioAttivo"
                />
              </div>
              
              <div v-if="isSocioAttivo" class="p-3 bg-blue-50 text-blue-800 border-round flex align-items-center gap-2 border-1 border-blue-200 mt-2">
                <i class="pi pi-info-circle text-lg"></i>
                <span class="text-sm">Sei un socio attivo. Puoi modificare la quota e il metodo di pagamento solo in fase di iscrizione o rinnovo.</span>
              </div>
            </div>
            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('4')" />
              <Button 
                label="Avanti" 
                icon="pi pi-arrow-right" 
                iconPos="right" 
                :disabled="!profile.payment_method || !profile.member_type" 
                @click="activateCallback('6')" 
              />
            </div>
          </StepPanel>

          <!-- 6️⃣ STEP: Riepilogo e Completamento -->
          <StepPanel v-slot="{ activateCallback }" value="6">
            <div class="py-3 text-left">
              <h3 class="font-semibold text-lg mb-3">Sintesi dati inseriti</h3>
              
              <div class="surface-ground p-4 border-round grid row-gap-3 column-gap-4">
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Nome e Cognome</span>
                  <span class="text-base text-900 font-medium">{{ profile.first_name }} {{ profile.last_name }}</span>
                </div>
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Codice Fiscale</span>
                  <span class="text-base text-900 font-medium uppercase">{{ profile.tax_code }}</span>
                </div>
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Data e Luogo Nascita</span>
                  <span class="text-base text-900 font-medium">{{ profile.birth_date ? profile.birth_date.toLocaleDateString() : '' }} - {{ profile.birth_place }}</span>
                </div>
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Telefono</span>
                  <span class="text-base text-900 font-medium">{{ profile.phone || '-' }}</span>
                </div>
                <div class="col-12 md:col-10 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Residenza</span>
                  <span class="text-base text-900 font-medium">{{ profile.address || '-' }}, {{ profile.city || '-' }} ({{ profile.province || '-' }}) - {{ profile.zip_code || '-' }}<template v-if="profile.municipio_roma"> - Municipio {{ profile.municipio_roma }}</template></span>
                </div>
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Documento</span>
                  <span class="text-base text-900 font-medium">{{ profile.document_type }} - {{ profile.document_number }} (Scad: {{ profile.document_expiry ? profile.document_expiry.toLocaleDateString() : '' }})</span>
                </div>
                <div class="col-12 md:col-5 flex flex-column gap-1">
                  <span class="text-xs font-semibold text-muted text-uppercase uppercase">Quota e Pagamento</span>
                  <span class="text-base text-900 font-medium">{{ profile.member_type }} - {{ profile.payment_method }}</span>
                </div>
              </div>

              <!-- Messaggio informativo di fine flusso -->
              <div v-if="backendUser?.status === 'INCOMPLETE'" class="mt-4 p-3 bg-blue-50 text-blue-800 border-round flex align-items-center gap-2 border-1 border-blue-200">
                <i class="pi pi-info-circle text-lg"></i>
                <span class="text-sm">Inviando la richiesta, la tua candidatura sarà sottoposta ad approvazione del consiglio direttivo.</span>
              </div>
            </div>
            
            <div class="flex pt-4 justify-content-between border-top-1 border-light">
              <Button label="Indietro" severity="secondary" icon="pi pi-arrow-left" @click="activateCallback('5')" />
              
              <Button 
                v-if="backendUser?.status === 'INCOMPLETE'" 
                label="Completa Iscrizione" 
                severity="success" 
                icon="pi pi-check" 
                @click="submit" 
              />
              <Button 
                v-else 
                label="Aggiorna Profilo" 
                severity="success" 
                icon="pi pi-save" 
                @click="submit" 
              />
            </div>
          </StepPanel>
        </StepPanels>
      </Stepper>
    </div>
  </div>
</template>

<style scoped>
.wizard-container {
  max-width: 1000px;
  margin: 0 auto;
}

.status-box {
  background-color: var(--accent-bg);
  border: 1px solid var(--accent-border);
  color: var(--text-h);
}

.surface-ground {
  background-color: var(--code-bg);
}

.text-muted {
  color: var(--text);
}

.border-light {
  border-color: var(--border);
}
</style>