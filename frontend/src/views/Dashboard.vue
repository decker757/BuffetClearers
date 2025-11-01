<template>
  <div>
    <!-- Hero Strip -->
    <section class="card p-3 mb-4">
      <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h4 class="fw-bold m-0">Real-Time AML Monitoring</h4>
          <div class="text-muted small">Upload a transaction CSV and analyze for suspicious activity.</div>
        </div>
      </div>
    </section>

    <!-- File Upload + Analyze -->
    <section class="card p-4 mb-4 text-center">
      <input
        ref="fileInput"
        type="file"
        accept=".csv"
        hidden
        @change="handleFile"
      />
      <button class="btn btn-outline-primary mb-3" @click="fileInput.click()">
        <i class="bi bi-upload me-2"></i>Select CSV File
      </button>
      <div v-if="fileName" class="text-muted mb-3">{{ fileName }}</div>

      <button
        class="btn btn-primary"
        :disabled="!transactions.length || analyzing"
        @click="analyze"
      >
        <i class="bi bi-cpu me-2"></i>
        {{ analyzing ? 'Analyzing…' : 'Analyze Transactions' }}
      </button>

      <div v-if="analyzing" class="mt-3">
        <div class="progress" style="height: 10px;">
          <div class="progress-bar progress-bar-striped progress-bar-animated" :style="{ width: progress + '%' }"></div>
        </div>
        <small class="text-muted">AI analysis in progress...</small>
      </div>
    </section>

    <!-- Summary -->
    <section v-if="results.length" class="card p-3 mb-4">
      <h6 class="fw-semibold mb-3">Risk Summary</h6>
      <div class="d-flex gap-3 flex-wrap">
        <div class="badge bg-danger fs-6 px-3 py-2">High: {{ summary.high }}</div>
        <div class="badge bg-warning text-dark fs-6 px-3 py-2">Medium: {{ summary.medium }}</div>
        <div class="badge bg-success fs-6 px-3 py-2">Low: {{ summary.low }}</div>
      </div>
    </section>

    <!-- Results Table -->
    <section v-if="results.length" class="card p-4">
      <h6 class="fw-semibold mb-3">Flagged Transactions</h6>
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead class="table-light">
            <tr>
              <th>#</th>
              <th>Account</th>
              <th>Jurisdiction</th>
              <th>Amount (USD)</th>
              <th>Risk Score</th>
              <th>Risk Level</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(tx, i) in sortedResults" :key="i" :class="rowClass(tx.risk)">
              <td>{{ i + 1 }}</td>
              <td>{{ tx.account }}</td>
              <td>{{ tx.jurisdiction }}</td>
              <td>{{ tx.amount.toLocaleString() }}</td>
              <td>{{ tx.score }}</td>
              <td>
                <span :class="riskBadge(tx.risk)" class="badge">{{ tx.risk }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const fileInput = ref(null)
const fileName = ref('')
const transactions = ref([])
const results = ref([])
const analyzing = ref(false)
const progress = ref(0)
const summary = ref({ high: 0, medium: 0, low: 0 })

function handleFile(e) {
  const file = e.target.files[0]
  if (!file) return
  fileName.value = file.name
  const reader = new FileReader()
  reader.onload = (ev) => {
    const text = ev.target.result
    parseCSV(text)
  }
  reader.readAsText(file)
}

function parseCSV(data) {
  const lines = data.trim().split('\n')
  const headers = lines.shift().split(',')
  transactions.value = lines.map(line => {
    const cols = line.split(',')
    const obj = {}
    headers.forEach((h, i) => obj[h.trim()] = cols[i]?.trim())
    return obj
  })
}

function analyze() {
  analyzing.value = true
  progress.value = 0
  results.value = []
  summary.value = { high: 0, medium: 0, low: 0 }

  const interval = setInterval(() => {
    progress.value += Math.floor(Math.random() * 10) + 10
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(interval)
      analyzing.value = false
      generateResults()
    }
  }, 300)
}

function generateResults() {
  // Dummy analysis: random risk scoring
  results.value = transactions.value.map(tx => {
    const score = Math.floor(Math.random() * 100)
    let risk = 'Low'
    if (score > 80) risk = 'High'
    else if (score > 50) risk = 'Medium'
    return {
      account: tx.Account || tx.account || tx.AccNo || '—',
      jurisdiction: tx.Jurisdiction || tx.Country || '—',
      amount: parseFloat(tx.Amount || tx.amount || 0),
      score, risk
    }
  })
  // Sort and summarize
  results.value.sort((a,b)=> b.score - a.score)
  summary.value = {
    high: results.value.filter(r=>r.risk==='High').length,
    medium: results.value.filter(r=>r.risk==='Medium').length,
    low: results.value.filter(r=>r.risk==='Low').length
  }
}

const sortedResults = computed(()=> results.value)
function riskBadge(risk) {
  if (risk==='High') return 'bg-danger'
  if (risk==='Medium') return 'bg-warning text-dark'
  return 'bg-success'
}
function rowClass(risk) {
  if (risk==='High') return 'table-danger'
  if (risk==='Medium') return 'table-warning'
  return ''
}
</script>
