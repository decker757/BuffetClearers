<template>
  <div class="container py-4">
    <h4 class="fw-bold text-primary mb-4">Document & Image Analysis</h4>

    <!-- Upload Section -->
    <div class="card shadow-sm p-4 mb-4 text-center">
      <input
        ref="fileInput"
        type="file"
        accept=".pdf,.doc,.docx,.txt,image/*"
        hidden
        @change="handleFile"
      />

      <button class="btn btn-outline-primary mb-3" @click="fileInput.click()">
        <i class="bi bi-upload me-2"></i>Select File
      </button>

      <div v-if="fileName" class="text-muted mb-3">
        <i class="bi bi-file-earmark me-1"></i>{{ fileName }}
      </div>

      <button
        class="btn btn-primary px-4"
        :disabled="!fileData || analyzing"
        @click="analyze"
      >
        <i class="bi bi-cpu me-2"></i>
        {{ analyzing ? "Analyzing…" : "Analyze File" }}
      </button>

      <!-- Progress Bar -->
      <div v-if="analyzing" class="mt-4">
        <div class="progress" style="height: 12px;">
          <div
            class="progress-bar progress-bar-striped progress-bar-animated"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <small class="text-muted">Running AI analysis...</small>
      </div>
    </div>

    <!-- Simplified Results -->
    <div v-if="summary" class="card shadow-sm p-4">
      <h5 class="fw-bold text-primary mb-3">{{ summary.fileName }}</h5>
      <p class="text-muted small mb-2">
        Analyzed on: {{ new Date(summary.analysisTime).toLocaleString() }}
      </p>

      <div class="d-flex flex-wrap gap-3 mb-3">
        <div><strong>Risk Score:</strong> {{ summary.riskScore }}</div>
        <div><strong>Severity:</strong> {{ summary.maxSeverity }}</div>
        <div><strong>Status:</strong> {{ summary.status }}</div>
      </div>

      <div class="alert alert-warning mb-3" v-if="summary.recommendation">
        <strong>Recommendation:</strong> {{ summary.recommendation }}
      </div>

      <h6 class="fw-semibold text-secondary">Action Items</h6>
      <ul class="mb-3">
        <li v-for="(a, i) in summary.actionItems" :key="i">
          <strong>{{ a.action }}</strong> — <em>{{ a.assignee }}</em>
          (Priority: {{ a.priority }})
        </li>
      </ul>

      <h6 class="fw-semibold text-secondary">Key Findings</h6>
      <ul class="small">
        <li v-for="(f, i) in summary.keyFindings" :key="i">{{ f }}</li>
      </ul>

      <h6 class="fw-semibold text-secondary mt-3">Risk Components</h6>
      <div v-for="(rf, i) in summary.riskFactors" :key="i" class="mb-2">
        <strong>{{ rf.component }}</strong> — {{ rf.severity }} (Score:
        {{ rf.score }})
        <ul class="small">
          <li v-for="(iss, j) in rf.issues" :key="j">{{ iss }}</li>
        </ul>
      </div>

      <details class="mt-3">
        <summary class="fw-semibold">View Raw JSON Response</summary>
        <pre class="bg-light p-3 mt-2 rounded small">{{ prettyResult }}</pre>
      </details>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";
import axios from "axios";

const fileInput = ref(null);
const fileName = ref("");
const fileData = ref(null);
const analyzing = ref(false);
const progress = ref(0);
const result = ref({});
const summary = ref(null);

const prettyResult = computed(() => JSON.stringify(result.value, null, 2));

function handleFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  fileName.value = file.name;
  fileData.value = file;
  result.value = {};
  summary.value = null;
}

async function analyze() {
  if (!fileData.value) {
    alert("Please select a file first.");
    return;
  }

  analyzing.value = true;
  progress.value = 10;
  result.value = {};
  summary.value = null;

  try {
    const formData = new FormData();
    formData.append("file", fileData.value);

    const ext = fileName.value.toLowerCase().split(".").pop();
    const isImage = ["jpg", "jpeg", "png", "bmp", "tiff", "gif"].includes(ext);
    const endpoint = isImage
      ? "http://localhost:5001/api/validate/image"
      : "http://localhost:5001/api/validate";

    const response = await axios.post(endpoint, formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (event) => {
        if (event.total)
          progress.value = Math.min(
            90,
            Math.round((event.loaded / event.total) * 100)
          );
      },
    });

    progress.value = 100;
    result.value = response.data;

    // Extract simplified summary
    const raw = response.data;
    summary.value = {
      fileName: raw?.file_metadata?.file_name || "Unknown",
      analysisTime: raw?.analysis_timestamp || "-",
      riskScore: raw?.summary?.overall_risk_score || 0,
      maxSeverity: raw?.summary?.max_severity || "N/A",
      recommendation: raw?.summary?.recommendation || "No recommendation",
      status: raw?.summary?.status || "UNKNOWN",
      actionItems:
        raw?.action_items?.map((a) => ({
          action: a.action,
          assignee: a.assignee,
          priority: a.priority,
        })) || [],
      keyFindings:
        raw?.detailed_analysis?.format_validation?.key_findings || [],
      riskFactors:
        raw?.risk_factors?.map((r) => ({
          component: r.component,
          severity: r.severity,
          score: r.score,
          issues: r.issues?.slice(0, 3) || [],
        })) || [],
    };
  } catch (err) {
    console.error("Error analyzing file:", err.response?.data || err.message);
    alert("Error contacting backend at /api/validate or /api/validate/image");
  } finally {
    analyzing.value = false;
  }
}
</script>

<style scoped>
.container {
  max-width: 800px;
}
.card {
  border-radius: 12px;
}
.btn {
  border-radius: 8px;
  font-weight: 500;
}
.progress-bar {
  background-color: #0d6efd;
  transition: width 0.3s ease;
}
ul {
  list-style-type: none;
  padding-left: 1.2em;
}
ul li {
  margin-bottom: 3px;
}
strong {
  color: #0d6efd;
}
pre {
  background: #f8f9fa;
  border-radius: 6px;
  overflow-x: auto;
}
.text-primary {
  color: #0d6efd !important;
}
</style>