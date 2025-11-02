<template>
  <div class="container py-4">
    <!-- Header -->
    <section class="card p-3 mb-4 shadow-sm border-0">
      <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h4 class="fw-bold m-0">Transaction Risk Analysis Dashboard</h4>
          <p class="text-muted small mb-0">
            Upload a CSV file to analyze transactions using Isolation Forest and XGBoost models.
          </p>
        </div>
        <div>
          <span class="badge bg-success me-2">API Connected</span>
          <button class="btn btn-outline-secondary btn-sm" @click="resetAnalysis">
            <i class="bi bi-arrow-clockwise me-1"></i>Reset
          </button>
        </div>
      </div>
    </section>

    <!-- File Upload -->
    <section class="card p-4 mb-4 border-0 shadow-sm text-center">
      <input ref="fileInput" type="file" accept=".csv" hidden @change="handleFile" />
      <button class="btn btn-outline-primary btn-lg mb-3" @click="fileInput.click()">
        <i class="bi bi-upload me-2"></i>Select Transaction CSV
      </button>

      <div v-if="fileName" class="text-muted mb-3">{{ fileName }}</div>

      <button
        class="btn btn-primary btn-lg"
        :disabled="!selectedFile || analyzing"
        @click="analyzeTransactions"
      >
        <i class="bi bi-cpu me-2"></i>
        {{ analyzing ? 'Analyzing Transactions…' : 'Analyze Transactions' }}
      </button>

      <div v-if="analyzing" class="mt-3">
        <div class="progress" style="height: 10px;">
          <div
            class="progress-bar progress-bar-striped progress-bar-animated"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <small class="text-muted">AI models running, please wait...</small>
      </div>
    </section>

    <!-- Results -->
    <section v-if="results" class="card p-4 border-0 shadow-sm">
      <h5 class="fw-semibold mb-3">Analysis Summary</h5>

      <div v-if="results.error" class="alert alert-danger">
        <strong>Error:</strong> {{ results.error }}
      </div>

      <div v-else>
        <p class="text-muted mb-3">
          Total Transactions: <strong>{{ results.total_transactions }}</strong><br />
          Method: <strong>{{ results.method }}</strong><br />
          Timestamp: <strong>{{ new Date(results.analysis_timestamp).toLocaleString() }}</strong>
        </p>

        <div v-if="results.xgboost" class="mb-4">
          <h6 class="fw-bold text-primary">XGBoost Results</h6>
          <ul>
            <li>Suspicious Transactions: {{ results.xgboost.suspicious_count }}</li>
            <li>Suspicious Percentage: {{ results.xgboost.suspicious_percentage }}%</li>
          </ul>
        </div>

        <div v-if="results.isolation_forest" class="mb-4">
          <h6 class="fw-bold text-danger">Isolation Forest Results</h6>
          <ul>
            <li>Anomalies Detected: {{ results.isolation_forest.anomaly_count }}</li>
            <li>Anomaly Percentage: {{ results.isolation_forest.anomaly_percentage }}%</li>
          </ul>
        </div>

        <div v-if="results.consensus" class="mb-4">
          <h6 class="fw-bold text-success">Consensus</h6>
          <ul>
            <li>Flagged by Both Models: {{ results.consensus.flagged_by_both }}</li>
            <li>XGBoost Only: {{ results.consensus.flagged_by_xgboost_only }}</li>
            <li>Isolation Forest Only: {{ results.consensus.flagged_by_isolation_forest_only }}</li>
          </ul>
        </div>

        <!-- Suspicious Table -->
        <div v-if="suspiciousTransactions.length" class="mt-4">
          <h6 class="fw-semibold mb-3">Flagged Transactions</h6>
          <div class="table-responsive">
            <table class="table table-hover align-middle">
              <thead class="table-light">
                <tr>
                  <th>#</th>
                  <th>Transaction ID</th>
                  <th>Amount</th>
                  <th>Probability / Score</th>
                  <th>Risk Level</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(tx, i) in suspiciousTransactions"
                  :key="i"
                  :class="{
                    'table-danger': tx.risk_level === 'High' || tx.anomaly_severity === 'High',
                    'table-warning': tx.risk_level === 'Medium' || tx.anomaly_severity === 'Medium'
                  }"
                >
                  <td>{{ i + 1 }}</td>
                  <td>{{ tx.transaction_id || '—' }}</td>
                  <td>{{ tx.amount?.toLocaleString() || '—' }}</td>
                  <td>
                    {{ tx.suspicion_probability?.toFixed?.(3) || tx.anomaly_score?.toFixed?.(3) || '—' }}
                  </td>
                  <td>
                    <span
                      class="badge"
                      :class="{
                        'bg-danger': tx.risk_level === 'High' || tx.anomaly_severity === 'High',
                        'bg-warning text-dark': tx.risk_level === 'Medium' || tx.anomaly_severity === 'Medium',
                        'bg-success': tx.risk_level === 'Low' || tx.anomaly_severity === 'Low'
                      }"
                    >
                      {{ tx.risk_level || tx.anomaly_severity || '—' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import axios from "axios";

const fileInput = ref(null);
const selectedFile = ref(null);
const fileName = ref("");
const analyzing = ref(false);
const progress = ref(0);
const results = ref(null);

function handleFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  fileName.value = file.name;
  selectedFile.value = file;
}

async function analyzeTransactions() {
  if (!selectedFile.value) return;

  analyzing.value = true;
  progress.value = 0;
  results.value = null;

  const formData = new FormData();
  formData.append("file", selectedFile.value);

  // Animate fake progress while waiting
  const timer = setInterval(() => {
    progress.value = Math.min(progress.value + Math.random() * 10, 95);
  }, 300);

  try {
    const res = await axios.post(
      "http://127.0.0.1:5001/api/analyze-transactions?method=both",
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    results.value = res.data;
  } catch (err) {
    results.value = { error: err.response?.data?.error || err.message };
  } finally {
    clearInterval(timer);
    progress.value = 100;
    analyzing.value = false;
  }
}

function resetAnalysis() {
  selectedFile.value = null;
  fileName.value = "";
  results.value = null;
}

const suspiciousTransactions = computed(() => {
  if (!results.value) return [];
  const all = [];
  if (results.value.xgboost?.suspicious_transactions)
    all.push(...results.value.xgboost.suspicious_transactions);
  if (results.value.isolation_forest?.anomalous_transactions)
    all.push(...results.value.isolation_forest.anomalous_transactions);
  return all;
});
</script>

<style scoped>
.container {
  max-width: 1100px;
}
.card {
  border-radius: 12px;
}
.table th,
.table td {
  vertical-align: middle;
}
.progress {
  background-color: #e9ecef;
}
</style>
