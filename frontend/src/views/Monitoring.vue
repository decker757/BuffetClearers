<template>
  <div>
    <h4 class="mb-4 fw-bold text-primary">Real-Time Transaction Monitoring</h4>

    <div class="card p-3">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <input v-model="search" class="form-control w-25" placeholder="Search by ID or jurisdiction" />
        <button class="btn btn-primary btn-sm" @click="refresh">Refresh</button>
      </div>

      <div class="table-responsive">
        <table class="table align-middle">
          <thead class="table-light">
            <tr>
              <th>ID</th>
              <th>Jurisdiction</th>
              <th>Amount (SGD)</th>
              <th>Risk Score</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tx in filteredTx" :key="tx.id">
              <td>{{ tx.id }}</td>
              <td>{{ tx.jurisdiction }}</td>
              <td>{{ tx.amount.toLocaleString() }}</td>
              <td>
                <div class="d-flex align-items-center gap-2">
                  <span :class="riskClass(tx.risk)" class="badge">{{ tx.risk }}</span>
                  <div class="progress flex-grow-1" style="height:6px">
                    <div class="progress-bar" :class="riskBarClass(tx.risk)" :style="{ width: tx.score + '%' }"></div>
                  </div>
                </div>
              </td>
              <td>
                <button class="btn btn-outline-primary btn-sm" @click="analyze(tx)">Analyze</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const search = ref('')
const transactions = ref([
  { id: 'T-1001', jurisdiction: 'SG', amount: 120000, risk: 'Low', score: 25 },
  { id: 'T-1002', jurisdiction: 'CH', amount: 980000, risk: 'High', score: 92 },
  { id: 'T-1003', jurisdiction: 'HK', amount: 32000, risk: 'Medium', score: 55 }
])

const filteredTx = computed(() =>
  transactions.value.filter(tx =>
    tx.id.toLowerCase().includes(search.value.toLowerCase()) ||
    tx.jurisdiction.toLowerCase().includes(search.value.toLowerCase())
  )
)

function riskClass(level) {
  return level === 'High'
    ? 'bg-danger'
    : level === 'Medium'
    ? 'bg-warning text-dark'
    : 'bg-success'
}

function riskBarClass(level) {
  return level === 'High'
    ? 'bg-danger'
    : level === 'Medium'
    ? 'bg-warning'
    : 'bg-success'
}

function analyze(tx) {
  alert(`AI analyzing ${tx.id}...`)
}

function refresh() {
  alert('Refreshing transaction feed...')
}
</script>
