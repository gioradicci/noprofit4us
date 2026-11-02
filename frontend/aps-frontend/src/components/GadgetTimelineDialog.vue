<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { API_URL, getImageUrl } from '../config.js'
import { supabase } from '../supabase'

import Dialog from 'primevue/dialog'
import Button from 'primevue/button'

const props = defineProps({
  visible: { type: Boolean, default: false },
  gadget: { type: Object, default: null }
})

const emit = defineEmits(['update:visible'])
const { t, locale } = useI18n()

const loading = ref(false)
const error = ref(false)
const timeline = ref(null)
let requestId = 0

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const headerTitle = computed(() => {
  const name = props.gadget?.name || timeline.value?.gadget?.name
  return name ? `${t('gadgets.timeline.title')} · ${name}` : t('gadgets.timeline.title')
})

const summary = computed(() => timeline.value?.summary || null)
const events = computed(() => timeline.value?.events || [])
const gadgetInfo = computed(() => timeline.value?.gadget || props.gadget || null)

const MOVEMENT_STYLES = {
  RESTOCK: { icon: 'pi pi-plus-circle', tone: 'restock' },
  TRANSFER: { icon: 'pi pi-arrows-h', tone: 'transfer' },
  DELIVERY: { icon: 'pi pi-send', tone: 'delivery' },
  LOAN: { icon: 'pi pi-briefcase', tone: 'loan' },
  LOAN_RETURN: { icon: 'pi pi-undo', tone: 'return' },
  LOAN_DELIVERY: { icon: 'pi pi-check-circle', tone: 'loanDelivery' }
}

const LEGEND_TYPES = ['RESTOCK', 'TRANSFER', 'DELIVERY', 'LOAN', 'LOAN_RETURN', 'LOAN_DELIVERY']

function movementStyle(type) {
  return MOVEMENT_STYLES[type] || { icon: 'pi pi-circle', tone: 'neutral' }
}

function movementLabel(type) {
  const key = `gadgets.timeline.movementTypes.${(type || '').toLowerCase()}`
  const translated = t(key)
  return translated === key ? t('gadgets.timeline.movementTypes.unknown') : translated
}

// La chip quantità mostra i pezzi movimentati (event.quantity), non il delta
// di saldo: per TRANSFER e LOAN_DELIVERY il saldo totale non cambia (delta 0)
// ma i pezzi spostati sono comunque significativi.
function quantityLabel(event) {
  const quantity = Number(event?.quantity || 0)
  switch (event?.movement_type) {
    case 'RESTOCK':
    case 'LOAN_RETURN':
      return `+${quantity}`
    case 'DELIVERY':
    case 'LOAN':
      return `-${quantity}`
    default:
      return String(quantity)
  }
}

function quantityTone(event) {
  switch (event?.movement_type) {
    case 'RESTOCK':
    case 'LOAN_RETURN':
      return 'delta-in'
    case 'DELIVERY':
    case 'LOAN':
      return 'delta-out'
    default:
      return 'delta-neutral'
  }
}

function quantityHint(event) {
  if (event?.movement_type === 'TRANSFER') return t('gadgets.timeline.transferHint')
  if (event?.movement_type === 'LOAN_DELIVERY') return t('gadgets.timeline.loanDeliveryHint')
  return null
}

function formatDateTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale.value || 'it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

function formatDate(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale.value || 'it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  }).format(date)
}

function performerLabel(event) {
  return event?.performer?.name || event?.performer?.email || t('gadgets.timeline.noPerformer')
}

function loanStatusLabel(status) {
  if (!status) return '-'
  const key = `gadgets.timeline.status.${status}`
  const translated = t(key)
  return translated === key ? status : translated
}

function eventSource(event) {
  switch (event.movement_type) {
    case 'LOAN':
      return event.from_warehouse?.name || t('gadgets.timeline.path.warehouse')
    case 'LOAN_RETURN':
    case 'LOAN_DELIVERY':
      return event.loan?.assigned_to_name || t('gadgets.timeline.path.assignee')
    case 'RESTOCK':
      return t('gadgets.timeline.path.external')
    default:
      return event.from_warehouse?.name || t('gadgets.timeline.path.external')
  }
}

function eventTarget(event) {
  switch (event.movement_type) {
    case 'LOAN':
      return event.loan?.assigned_to_name || t('gadgets.timeline.path.assignee')
    case 'LOAN_RETURN':
      return event.to_warehouse?.name || t('gadgets.timeline.path.warehouse')
    case 'LOAN_DELIVERY':
      return t('gadgets.timeline.path.member')
    case 'RESTOCK':
    case 'TRANSFER':
      return event.to_warehouse?.name || t('gadgets.timeline.path.warehouse')
    default:
      return t('gadgets.timeline.path.member')
  }
}

const terminalState = computed(() => {
  if (!summary.value) return null
  if ((summary.value.current_stock || 0) <= 0) {
    return (summary.value.open_loans_remaining || 0) > 0 ? 'inCustody' : 'exhausted'
  }
  return 'remaining'
})

const terminalInfo = computed(() => {
  const data = summary.value
  if (!data || !terminalState.value) return null
  if (terminalState.value === 'exhausted') {
    return {
      icon: 'pi pi-check-circle',
      tone: 'restock',
      title: t('gadgets.timeline.terminal.exhaustedTitle'),
      detail: t('gadgets.timeline.terminal.exhaustedDetail')
    }
  }
  if (terminalState.value === 'inCustody') {
    return {
      icon: 'pi pi-briefcase',
      tone: 'loan',
      title: t('gadgets.timeline.terminal.inCustodyTitle'),
      detail: t('gadgets.timeline.terminal.inCustodyDetail', { count: data.open_loans_remaining || 0 })
    }
  }
  return {
    icon: 'pi pi-box',
    tone: 'transfer',
    title: t('gadgets.timeline.terminal.remainingTitle'),
    detail: t('gadgets.timeline.terminal.remainingDetail', { count: data.current_stock || 0 })
  }
})

async function loadTimeline() {
  if (!props.gadget?.id) return
  const currentRequest = ++requestId
  loading.value = true
  error.value = false
  timeline.value = null

  try {
    const session = (await supabase.auth.getSession()).data.session
    const token = session?.access_token
    const response = await fetch(`${API_URL}/gadgets/${props.gadget.id}/timeline`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    if (currentRequest !== requestId) return
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    if (currentRequest !== requestId) return
    timeline.value = data
  } catch (err) {
    if (currentRequest !== requestId) return
    console.error('Errore nel caricamento della timeline gadget:', err)
    error.value = true
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}

watch(
  () => [props.visible, props.gadget?.id],
  ([visible]) => {
    if (visible && props.gadget?.id) loadTimeline()
    if (!visible) requestId += 1
  }
)
</script>

<template>
  <Dialog
    v-model:visible="dialogVisible"
    :header="headerTitle"
    :modal="true"
    :draggable="false"
    :style="{ width: '95vw', maxWidth: '780px', height: '90vh' }"
    :contentStyle="{ maxHeight: 'calc(90vh - 8rem)', overflowY: 'auto', paddingTop: '0.5rem' }"
    class="gadget-timeline-dialog"
  >
    <div v-if="loading" class="flex flex-column align-items-center justify-content-center gap-3 py-8">
      <i class="pi pi-spin pi-spinner text-4xl text-primary"></i>
      <p class="m-0 text-color-secondary">{{ t('gadgets.timeline.loading') }}</p>
    </div>

    <div v-else-if="error" class="flex flex-column align-items-center justify-content-center gap-3 py-8">
      <i class="pi pi-exclamation-triangle text-4xl text-red-500"></i>
      <p class="m-0 text-color-secondary text-center">{{ t('gadgets.timeline.loadFailed') }}</p>
      <Button :label="t('gadgets.timeline.retry')" icon="pi pi-refresh" severity="secondary" outlined @click="loadTimeline" />
    </div>

    <div v-else-if="timeline" class="timeline-content">
      <!-- Intestazione articolo -->
      <div class="gadget-head">
        <div class="gadget-thumb">
          <img
            v-if="gadgetInfo?.image_path"
            :src="getImageUrl(gadgetInfo.image_path)"
            :alt="gadgetInfo.name"
            loading="lazy"
            decoding="async"
          />
          <i v-else class="pi pi-image text-color-secondary"></i>
        </div>
        <div class="flex-1 min-w-0">
          <h3 class="m-0 text-lg font-bold text-900">{{ gadgetInfo?.name || '-' }}</h3>
          <div class="flex flex-wrap align-items-center gap-2 mt-1">
            <span class="text-xs text-secondary">{{ gadgetInfo?.sku || '-' }}</span>
            <span class="badge category-badge">{{ gadgetInfo?.category || '-' }}</span>
            <span v-if="gadgetInfo?.is_not_for_sale" class="badge not-for-sale-badge">
              <i class="pi pi-ban text-xs mr-1"></i>{{ t('gadgets.table.notForSaleShort') }}
            </span>
          </div>
        </div>
      </div>

      <p class="timeline-subtitle">{{ t('gadgets.timeline.subtitle') }}</p>

      <!-- Riepilogo numerico -->
      <div class="summary-grid">
        <div class="summary-card">
          <span class="summary-label">{{ t('gadgets.timeline.summary.restocked') }}</span>
          <span class="summary-value text-green-600">{{ summary.total_restocked }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">{{ t('gadgets.timeline.summary.delivered') }}</span>
          <span class="summary-value text-red-600">{{ summary.total_delivered }}</span>
        </div>
        <div class="summary-card">
          <span class="summary-label">{{ t('gadgets.timeline.summary.loaned') }}</span>
          <span class="summary-value text-purple-600">{{ summary.total_loaned }}</span>
          <span class="summary-hint">
            {{ t('gadgets.timeline.summary.returned') }}: {{ summary.total_loan_returns }} ·
            {{ t('gadgets.timeline.summary.deliveredFromLoan') }}: {{ summary.total_loan_deliveries }}
          </span>
        </div>
        <div class="summary-card">
          <span class="summary-label">{{ t('gadgets.timeline.summary.currentStock') }}</span>
          <span class="summary-value" :class="summary.current_stock > 0 ? 'text-blue-600' : 'text-red-600'">
            {{ summary.current_stock }}
          </span>
          <span class="summary-hint">
            {{ t('gadgets.timeline.summary.inCustody') }}: {{ summary.open_loans_remaining }}
          </span>
        </div>
      </div>

      <div class="summary-meta">
        <span v-if="summary.first_restock_at">
          <i class="pi pi-calendar text-xs mr-1"></i>
          {{ t('gadgets.timeline.summary.firstRestock') }}: {{ formatDateTime(summary.first_restock_at) }}
        </span>
        <span>
          <i class="pi pi-list text-xs mr-1"></i>
          {{ t('gadgets.timeline.summary.movements') }}: {{ summary.movements_count }}
        </span>
        <span v-if="summary.open_loans_count > 0" class="open-loans-meta">
          <i class="pi pi-briefcase text-xs mr-1"></i>
          {{ t('gadgets.timeline.summary.openLoans') }}: {{ summary.open_loans_count }}
        </span>
      </div>

      <div v-if="!summary.is_reconciled" class="warning-box">
        <i class="pi pi-exclamation-triangle mr-2"></i>
        {{ t('gadgets.timeline.notReconciled') }}
        ({{ t('gadgets.timeline.balanceAfter') }}: {{ summary.current_stock }} ·
        {{ t('gadgets.timeline.summary.gadgetStock') }}: {{ summary.gadget_stock_quantity }})
      </div>

      <div v-if="summary.unlinked_loans_count > 0" class="warning-box warning-box-soft">
        <i class="pi pi-question-circle mr-2"></i>
        {{ t('gadgets.timeline.unlinkedLoansWarning', { count: summary.unlinked_loans_count }) }}
      </div>

      <!-- Legenda -->
      <div class="legend">
        <span class="legend-title">{{ t('gadgets.timeline.legend') }}:</span>
        <span v-for="type in LEGEND_TYPES" :key="type" class="legend-item">
          <i :class="movementStyle(type).icon" :style="{ color: `var(--tone-${movementStyle(type).tone})` }"></i>
          {{ movementLabel(type) }}
        </span>
      </div>

      <!-- Timeline -->
      <div v-if="!events.length" class="empty-box">
        <i class="pi pi-history text-3xl text-400 mb-2"></i>
        <p class="m-0 text-color-secondary">{{ t('gadgets.timeline.empty') }}</p>
      </div>

      <ol v-else class="timeline">
        <li v-for="event in events" :key="event.id" class="timeline-item">
          <span class="timeline-marker" :class="'tone-' + movementStyle(event.movement_type).tone">
            <i :class="movementStyle(event.movement_type).icon"></i>
          </span>

          <div class="timeline-card">
            <div class="event-header">
              <span class="badge type-badge" :class="'tone-' + movementStyle(event.movement_type).tone">
                {{ movementLabel(event.movement_type) }}
              </span>
              <span class="event-date">{{ formatDateTime(event.timestamp) }}</span>
            </div>

            <div class="event-path">
              <span class="path-node">{{ eventSource(event) }}</span>
              <i class="pi pi-arrow-right text-xs mx-2 text-400"></i>
              <span class="path-node">{{ eventTarget(event) }}</span>
              <span class="qty-chip ml-2" :class="quantityTone(event)" :title="quantityHint(event) || undefined">
                {{ quantityLabel(event) }} {{ t('gadgets.timeline.pcs') }}
              </span>
            </div>

            <p v-if="event.notes" class="event-notes">{{ event.notes }}</p>

            <div class="event-meta">
              <span><i class="pi pi-user text-xs mr-1"></i>{{ performerLabel(event) }}</span>
              <span class="balance-chip">
                {{ t('gadgets.timeline.balanceAfter') }}: {{ event.balance_after ?? '-' }} {{ t('gadgets.timeline.pcs') }}
              </span>
            </div>

            <!-- Rami affidamento -->
            <div v-if="event.loan" class="loan-panel">
              <div class="flex flex-wrap align-items-center gap-2">
                <span class="loan-ref">{{ t('gadgets.timeline.loanReference', { id: event.loan.id }) }}</span>
                <span class="badge loan-status" :class="'loan-status-' + (event.loan.status || '').toLowerCase()">
                  {{ loanStatusLabel(event.loan.status) }}
                </span>
                <span v-if="event.loan.is_open" class="badge open-branch-badge">
                  <i class="pi pi-exclamation-circle text-xs mr-1"></i>{{ t('gadgets.timeline.openBranch') }}
                </span>
                <span v-if="event.loan_link_source === 'heuristic'" class="badge heuristic-badge">
                  {{ t('gadgets.timeline.linkedHeuristicShort') }}
                </span>
              </div>

              <div class="loan-facts">
                <span>
                  <strong>{{ t('gadgets.timeline.loanAssignedTo') }}:</strong>
                  {{ event.loan.assigned_to_name || '-' }}
                </span>
                <span>
                  <strong>{{ t('gadgets.timeline.loanRemaining') }}:</strong>
                  {{ event.loan.remaining_quantity }} {{ t('gadgets.timeline.pcs') }}
                </span>
                <span v-if="event.loan.expected_return_date">
                  <strong>{{ t('gadgets.timeline.loanExpectedReturn') }}:</strong>
                  {{ formatDate(event.loan.expected_return_date) }}
                </span>
              </div>

              <p v-if="event.loan.is_open && !event.children.length" class="open-hint">
                <i class="pi pi-info-circle mr-1"></i>{{ t('gadgets.timeline.openBranchHint') }}
              </p>
            </div>

            <ul v-if="event.children.length" class="loan-children">
              <li v-for="child in event.children" :key="child.id" class="loan-child">
                <span class="child-marker" :class="'tone-' + movementStyle(child.movement_type).tone">
                  <i :class="movementStyle(child.movement_type).icon"></i>
                </span>
                <div class="child-card">
                  <div class="event-header">
                    <span class="badge type-badge" :class="'tone-' + movementStyle(child.movement_type).tone">
                      {{ movementLabel(child.movement_type) }}
                    </span>
                    <span class="event-date">{{ formatDateTime(child.timestamp) }}</span>
                  </div>
                  <div class="event-path">
                    <span class="path-node">{{ eventSource(child) }}</span>
                    <i class="pi pi-arrow-right text-xs mx-2 text-400"></i>
                    <span class="path-node">{{ eventTarget(child) }}</span>
                    <span class="qty-chip ml-2" :class="quantityTone(child)" :title="quantityHint(child) || undefined">
                      {{ quantityLabel(child) }} {{ t('gadgets.timeline.pcs') }}
                    </span>
                  </div>
                  <p v-if="child.notes" class="event-notes">{{ child.notes }}</p>
                  <div class="event-meta">
                    <span><i class="pi pi-user text-xs mr-1"></i>{{ performerLabel(child) }}</span>
                    <span class="balance-chip">
                      {{ t('gadgets.timeline.balanceAfter') }}: {{ child.balance_after ?? '-' }} {{ t('gadgets.timeline.pcs') }}
                    </span>
                  </div>
                  <span v-if="child.loan_link_source === 'heuristic'" class="badge heuristic-badge mt-1">
                    {{ t('gadgets.timeline.linkedHeuristicShort') }}
                  </span>
                  <span v-else-if="child.loan_link_source === 'none'" class="badge unlinked-badge mt-1">
                    {{ t('gadgets.timeline.linkedNoneShort') }}
                  </span>
                </div>
              </li>
            </ul>

            <span v-else-if="!event.loan && ['LOAN_RETURN', 'LOAN_DELIVERY'].includes(event.movement_type)" class="badge unlinked-badge mt-2">
              {{ t('gadgets.timeline.linkedNoneShort') }}
            </span>
          </div>
        </li>

        <!-- Nodo terminale -->
        <li v-if="terminalInfo" class="timeline-item terminal-item">
          <span class="timeline-marker" :class="'tone-' + terminalInfo.tone">
            <i :class="terminalInfo.icon"></i>
          </span>
          <div class="timeline-card terminal-card">
            <h4 class="m-0 text-base font-bold text-900">{{ terminalInfo.title }}</h4>
            <div class="m-0 mt-2 terminal-facts">
              <span class="terminal-fact">
                <i class="pi pi-briefcase text-xs mr-1"></i>
                {{ terminalInfo.detail }} {{ t('gadgets.timeline.pcs') }}
              </span>
            </div>
            <p v-if="summary.stock_by_warehouse?.length" class="m-0 mt-2 warehouse-list">
              <span v-for="stock in summary.stock_by_warehouse" :key="stock.warehouse_id" class="warehouse-item">
                <i class="pi pi-warehouse text-xs mr-1"></i>
                {{ stock.warehouse_name || stock.warehouse_code }}: {{ stock.quantity }} {{ t('gadgets.timeline.pcs') }}
              </span>
            </p>

            <!-- Totale affidati e pezzi ancora nel circuito -->
            <div class="m-0 mt-2 terminal-facts">
              <span class="terminal-fact">
                <i class="pi pi-briefcase text-xs mr-1"></i>
                <strong>{{ t('gadgets.timeline.terminal.totalLoaned') }}:</strong>
                {{ summary.total_loaned }} {{ t('gadgets.timeline.pcs') }}
              </span>
              <span class="terminal-fact-detail">
                {{ t('gadgets.timeline.summary.returned') }}: {{ summary.total_loan_returns }} ·
                {{ t('gadgets.timeline.summary.deliveredFromLoan') }}: {{ summary.total_loan_deliveries }} ·
                {{ t('gadgets.timeline.summary.inCustody') }}: {{ summary.open_loans_remaining }}
              </span>
            </div>
            <div class="m-0 mt-1 terminal-facts">
              <span class="terminal-fact">
                <i class="pi pi-box text-xs mr-1"></i>
                <strong>{{ t('gadgets.timeline.terminal.stillInCircuit') }}:</strong>
                {{ (summary.current_stock || 0) + (summary.open_loans_remaining || 0) }} {{ t('gadgets.timeline.pcs') }}
              </span>
              <span class="terminal-fact-detail">
                {{ t('gadgets.timeline.summary.currentStock') }}: {{ summary.current_stock }} +
                {{ t('gadgets.timeline.summary.inCustody') }}: {{ summary.open_loans_remaining }}
              </span>
            </div>

            <span v-if="summary.is_reconciled" class="badge reconciled-badge mt-2">
              <i class="pi pi-check text-xs mr-1"></i>{{ t('gadgets.timeline.reconciled') }}
            </span>
          </div>
        </li>
      </ol>
    </div>

    <template #footer>
      <Button :label="t('gadgets.timeline.close')" severity="secondary" outlined @click="dialogVisible = false" />
    </template>
  </Dialog>
</template>

<style scoped>
.gadget-timeline-dialog :deep(.p-dialog-header) {
  padding-bottom: 0.5rem;
}

.timeline-content {
  text-align: left;
}

.gadget-head {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  padding: 0.5rem 0;
}

.gadget-thumb {
  width: 46px;
  height: 62px;
  flex-shrink: 0;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--code-bg, #f8fafc);
}

.gadget-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.15rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  line-height: 1.35;
  white-space: nowrap;
}

.category-badge {
  background: #e0f2fe;
  color: #0369a1;
}

.not-for-sale-badge {
  background: #ffedd5;
  color: #c2410c;
}

.timeline-subtitle {
  margin: 0.25rem 0 0.75rem;
  font-size: 0.8rem;
  color: var(--p-text-muted-color, #64748b);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.summary-card {
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  padding: 0.5rem 0.65rem;
  background: var(--code-bg, #f8fafc);
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.summary-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  font-weight: 700;
  color: var(--p-text-muted-color, #64748b);
}

.summary-value {
  font-size: 1.35rem;
  font-weight: 800;
  line-height: 1.1;
}

.summary-hint {
  font-size: 0.66rem;
  color: var(--p-text-muted-color, #64748b);
}

.summary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin: 0.6rem 0 0.35rem;
  font-size: 0.72rem;
  color: var(--p-text-muted-color, #64748b);
}

.open-loans-meta {
  color: #7c3aed;
  font-weight: 700;
}

.warning-box {
  margin-top: 0.5rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  background: #fef3c7;
  color: #92400e;
  font-size: 0.75rem;
  font-weight: 600;
}

.warning-box-soft {
  background: #ede9fe;
  color: #5b21b6;
  font-weight: 500;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.85rem;
  margin: 0.75rem 0;
  font-size: 0.7rem;
  color: var(--p-text-muted-color, #64748b);
}

.legend-title {
  font-weight: 700;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem 0;
  text-align: center;
}

.timeline {
  list-style: none;
  margin: 0;
  padding: 0;
  position: relative;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 15px;
  top: 6px;
  bottom: 18px;
  width: 2px;
  background: var(--border, #e5e7eb);
}

.timeline-item {
  position: relative;
  padding-left: 44px;
  margin-bottom: 1rem;
}

.timeline-marker {
  position: absolute;
  left: 0;
  top: 2px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--tone, #94a3b8);
  background: var(--tone-bg, #f1f5f9);
  color: var(--tone, #475569);
  z-index: 1;
  font-size: 0.9rem;
}

.timeline-card {
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  padding: 0.65rem 0.75rem;
  background: var(--p-content-background, #ffffff);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  min-width: 0;
}

.event-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
}

.event-date {
  font-size: 0.7rem;
  color: var(--p-text-muted-color, #64748b);
  white-space: nowrap;
}

.type-badge {
  background: var(--tone-bg, #f1f5f9);
  color: var(--tone, #475569);
}

.event-path {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  margin-top: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--p-text-color, #0f172a);
  overflow-wrap: anywhere;
}

.path-node {
  max-width: 100%;
}

.qty-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
  font-size: 0.72rem;
  font-weight: 800;
}

.delta-in {
  background: #dcfce7;
  color: #15803d;
}

.delta-out {
  background: #fee2e2;
  color: #b91c1c;
}

.delta-neutral {
  background: #e2e8f0;
  color: #475569;
}

.event-notes {
  margin: 0.4rem 0 0;
  font-size: 0.75rem;
  color: var(--p-text-color, #334155);
  overflow-wrap: anywhere;
}

.event-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.35rem;
  margin-top: 0.45rem;
  font-size: 0.7rem;
  color: var(--p-text-muted-color, #64748b);
}

.balance-chip {
  font-weight: 700;
  color: var(--p-text-color, #334155);
  background: var(--code-bg, #f1f5f9);
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
}

.loan-panel {
  margin-top: 0.55rem;
  padding: 0.5rem 0.6rem;
  border-radius: 8px;
  background: #f5f3ff;
  border: 1px solid #ddd6fe;
}

.loan-ref {
  font-size: 0.72rem;
  font-weight: 800;
  color: #5b21b6;
}

.loan-status {
  background: #ede9fe;
  color: #6d28d9;
}

.loan-status-active {
  background: #ede9fe;
  color: #6d28d9;
}

.loan-status-partial {
  background: #fef3c7;
  color: #b45309;
}

.loan-status-returned {
  background: #ccfbf1;
  color: #0f766e;
}

.loan-status-delivered,
.loan-status-completed {
  background: #e0e7ff;
  color: #4338ca;
}

.open-branch-badge {
  background: #ffe4e6;
  color: #be123c;
}

.heuristic-badge {
  background: #fef3c7;
  color: #92400e;
}

.unlinked-badge {
  background: #f1f5f9;
  color: #64748b;
}

.loan-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.9rem;
  margin-top: 0.35rem;
  font-size: 0.72rem;
  color: #4c1d95;
  overflow-wrap: anywhere;
}

.open-hint {
  margin: 0.4rem 0 0;
  font-size: 0.7rem;
  color: #9f1239;
}

.loan-children {
  list-style: none;
  margin: 0.6rem 0 0;
  padding: 0 0 0 0.55rem;
  border-left: 2px dashed #c4b5fd;
}

.loan-child {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  padding-left: 0.55rem;
  margin-bottom: 0.55rem;
}

.loan-child::before {
  content: '';
  position: absolute;
  left: -0.55rem;
  top: 12px;
  width: 0.55rem;
  border-top: 2px dashed #c4b5fd;
}

.child-marker {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--tone, #94a3b8);
  background: var(--tone-bg, #f1f5f9);
  color: var(--tone, #475569);
  font-size: 0.7rem;
  margin-top: 4px;
}

.child-card {
  flex: 1;
  min-width: 0;
  border: 1px solid #ede9fe;
  border-radius: 8px;
  padding: 0.45rem 0.55rem;
  background: #ffffff;
}

.terminal-card {
  border-style: dashed;
  border-width: 2px;
  background: var(--code-bg, #f8fafc);
}

.warehouse-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 0.85rem;
  font-size: 0.7rem;
  color: var(--p-text-muted-color, #64748b);
}

.terminal-facts {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.2rem 0.85rem;
  font-size: 0.72rem;
  color: var(--p-text-color, #334155);
}

.terminal-fact {
  font-weight: 600;
}

.terminal-fact-detail {
  font-size: 0.68rem;
  color: var(--p-text-muted-color, #64748b);
}

.reconciled-badge {
  background: #dcfce7;
  color: #15803d;
}

.tone-restock {
  --tone: #16a34a;
  --tone-bg: #dcfce7;
}

.tone-transfer {
  --tone: #2563eb;
  --tone-bg: #dbeafe;
}

.tone-delivery {
  --tone: #dc2626;
  --tone-bg: #fee2e2;
}

.tone-loan {
  --tone: #7c3aed;
  --tone-bg: #ede9fe;
}

.tone-return {
  --tone: #0d9488;
  --tone-bg: #ccfbf1;
}

.tone-loanDelivery {
  --tone: #4f46e5;
  --tone-bg: #e0e7ff;
}

.tone-neutral {
  --tone: #64748b;
  --tone-bg: #f1f5f9;
}

@media (min-width: 576px) {
  .summary-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 575px) {
  .timeline::before {
    left: 12px;
  }

  .timeline-item {
    padding-left: 36px;
  }

  .timeline-marker {
    width: 26px;
    height: 26px;
    font-size: 0.75rem;
  }

  .event-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .loan-child {
    padding-left: 0.15rem;
  }
}
</style>
