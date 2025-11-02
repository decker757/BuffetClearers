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

    <!-- Results -->
    <div v-if="Object.keys(result).length" class="card shadow-sm p-4">
      <h6 class="fw-semibold mb-3 text-primary">Analysis Results</h6>

      <div class="result-table">
        <div
          v-for="(value, key) in result"
          :key="key"
          class="result-row mb-2"
        >
          <strong class="text-capitalize">{{ formatKey(key) }}:</strong>
          <span>
            <template v-if="Array.isArray(value)">
              <ul class="mt-1 mb-1">
                <li v-for="(item, idx) in value" :key="idx">
                  {{ formatValue(item) }}
                </li>
              </ul>
            </template>
            <template v-else-if="typeof value === 'object' && value !== null">
              <ul class="mt-1 mb-1 ps-3">
                <li v-for="(subVal, subKey) in value" :key="subKey">
                  <strong>{{ formatKey(subKey) }}:</strong> {{ formatValue(subVal) }}
                </li>
              </ul>
            </template>
            <template v-else>
              {{ formatValue(value) }}
            </template>
          </span>
        </div>
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

const prettyResult = computed(() => JSON.stringify(result.value, null, 2));

function handleFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  fileName.value = file.name;
  fileData.value = file;
  result.value = {};
}

function formatKey(key) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatValue(value) {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toFixed(2);
  return value;
}

async function analyze() {
  if (!fileData.value) {
    alert("Please select a file first.");
    return;
  }

  analyzing.value = true;
  progress.value = 10;
  result.value = {};

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
.result-table {
  line-height: 1.6;
}
.result-row strong {
  display: inline-block;
  min-width: 180px;
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
