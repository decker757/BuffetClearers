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
        <!-- Audit Info -->
        <div class="alert alert-info mb-3">
          <small>
            <strong>Execution ID:</strong> {{ results.execution_id }}<br />
            <strong>Analysis Timestamp:</strong> {{ new Date(results.analysis_timestamp).toLocaleString() }}<br />
            <strong>Data Source:</strong> {{ results.data_source }}
          </small>
        </div>

        <p class="text-muted mb-3">
          Total Transactions: <strong>{{ results.total_transactions }}</strong><br />
          Method: <strong>{{ results.analysis_config?.method || 'both' }}</strong>
        </p>

        <!-- Summary Statistics -->
        <div v-if="results.summary_statistics" class="row mb-4">
          <div class="col-md-4">
            <div class="card bg-light border-0 p-3">
              <h6 class="text-muted small mb-2">Fraud Score (Avg)</h6>
              <h4 class="mb-0">{{ results.summary_statistics.fraud_scores?.average?.toFixed(1) || 'N/A' }}</h4>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card bg-danger text-white border-0 p-3">
              <h6 class="small mb-2">High Risk</h6>
              <h4 class="mb-0">{{ results.summary_statistics.risk_categories?.high || 0 }}</h4>
            </div>
          </div>
          <div class="col-md-4">
            <div class="card bg-warning border-0 p-3">
              <h6 class="small mb-2">Total Alerts</h6>
              <h4 class="mb-0">{{ results.summary_statistics.total_alerts_triggered || 0 }}</h4>
            </div>
          </div>
        </div>

        <div v-if="results.model_results?.xgboost" class="mb-4">
          <h6 class="fw-bold text-primary">XGBoost Results</h6>
          <ul>
            <li>Suspicious Transactions: {{ results.model_results.xgboost.suspicious_count }}</li>
            <li>Suspicious Percentage: {{ results.model_results.xgboost.suspicious_percentage }}%</li>
            <li>Risk Distribution:
              <span class="badge bg-danger ms-2">High: {{ results.model_results.xgboost.risk_distribution?.high || 0 }}</span>
              <span class="badge bg-warning text-dark ms-1">Med: {{ results.model_results.xgboost.risk_distribution?.medium || 0 }}</span>
              <span class="badge bg-success ms-1">Low: {{ results.model_results.xgboost.risk_distribution?.low || 0 }}</span>
            </li>
          </ul>
        </div>

        <div v-if="results.model_results?.isolation_forest" class="mb-4">
          <h6 class="fw-bold text-danger">Isolation Forest Results</h6>
          <ul>
            <li>Anomalies Detected: {{ results.model_results.isolation_forest.anomaly_count }}</li>
            <li>Anomaly Percentage: {{ results.model_results.isolation_forest.anomaly_percentage }}%</li>
            <li>Severity Distribution:
              <span class="badge bg-danger ms-2">High: {{ results.model_results.isolation_forest.severity_distribution?.high || 0 }}</span>
              <span class="badge bg-warning text-dark ms-1">Med: {{ results.model_results.isolation_forest.severity_distribution?.medium || 0 }}</span>
              <span class="badge bg-success ms-1">Low: {{ results.model_results.isolation_forest.severity_distribution?.low || 0 }}</span>
            </li>
          </ul>
        </div>

        <div v-if="results.consensus" class="mb-4">
          <h6 class="fw-bold text-success">Consensus (High Confidence)</h6>
          <ul>
            <li>High Confidence: {{ results.consensus.high_confidence_count || 0 }} transactions ({{ results.consensus.high_confidence_percentage || 0 }}%)</li>
          </ul>
        </div>

        <!-- Regulatory Compliance -->
        <div v-if="results.summary_statistics?.regulatory_compliance" class="mb-4">
          <h6 class="fw-bold text-warning">Regulatory Compliance</h6>
          <ul>
            <li>Total Violations: {{ results.summary_statistics.regulatory_compliance.total_violations }}</li>
            <li>Transactions with Violations: {{ results.summary_statistics.regulatory_compliance.transactions_with_violations }}</li>
            <li>Compliance Rate: {{ results.summary_statistics.regulatory_compliance.compliance_rate?.toFixed(1) }}%</li>
          </ul>
        </div>

        <!-- Enhanced Transactions Table (Top 100 by risk) -->
        <div v-if="enhancedTransactions.length" class="mt-4">
          <h6 class="fw-semibold mb-3">
            Top Flagged Transactions
            <span class="badge bg-secondary">{{ enhancedTransactions.length }}</span>
          </h6>
          <div class="table-responsive">
            <table class="table table-hover align-middle">
              <thead class="table-light">
                <tr>
                  <th>#</th>
                  <th>Transaction ID</th>
                  <th>Amount</th>
                  <th>Fraud Score</th>
                  <th>Risk Category</th>
                  <th>Alerts</th>
                  <th>Violations</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(tx, i) in enhancedTransactions.slice(0, 20)"
                  :key="i"
                  :class="{
                    'table-danger': tx.risk_category === 'CRITICAL',
                    'table-warning': tx.risk_category === 'HIGH' || tx.risk_category === 'MEDIUM'
                  }"
                >
                  <td>{{ i + 1 }}</td>
                  <td><small class="font-monospace">{{ tx.transaction_id || '—' }}</small></td>
                  <td>${{ (tx.amount || 0).toLocaleString() }}</td>
                  <td>
                    <strong :class="{
                      'text-danger': tx.fraud_risk_score >= 80,
                      'text-warning': tx.fraud_risk_score >= 60 && tx.fraud_risk_score < 80,
                      'text-secondary': tx.fraud_risk_score < 60
                    }">
                      {{ tx.fraud_risk_score?.toFixed(1) || '—' }}
                    </strong>
                  </td>
                  <td>
                    <span
                      class="badge"
                      :class="{
                        'bg-danger': tx.risk_category === 'CRITICAL',
                        'bg-warning text-dark': tx.risk_category === 'HIGH',
                        'bg-info text-dark': tx.risk_category === 'MEDIUM',
                        'bg-secondary': tx.risk_category === 'LOW'
                      }"
                    >
                      {{ tx.risk_category || '—' }}
                    </span>
                  </td>
                  <td>
                    <span class="badge bg-dark">{{ tx.alert_count || 0 }}</span>
                    <small v-if="tx.alerts && tx.alerts.length" class="d-block text-muted mt-1">
                      {{ tx.alerts[0]?.rule || '' }}
                    </small>
                  </td>
                  <td>
                    <span v-if="tx.violation_count" class="badge bg-warning text-dark">
                      {{ tx.violation_count }}
                    </span>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <p class="text-muted small mt-2">
            <i class="bi bi-info-circle me-1"></i>
            Showing top 20 of {{ enhancedTransactions.length }} flagged transactions, sorted by fraud risk score
          </p>
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

// Use enhanced_transactions from new API response
const enhancedTransactions = computed(() => {
  if (!results.value) return [];
  // New enhanced API returns enhanced_transactions array
  if (results.value.enhanced_transactions) {
    return results.value.enhanced_transactions;
  }
  // Fallback for old API format
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
