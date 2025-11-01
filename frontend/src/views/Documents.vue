<template>
  <div>
    <h4 class="mb-4 fw-bold text-primary">Document & Image Corroboration</h4>

    <!-- Upload Zone -->
    <div class="card p-4 mb-4">
      <FileUpload @files-selected="handleFiles" />
      <div v-if="uploadedFiles.length" class="mt-3 text-end">
        <button
          class="btn btn-primary btn-lg px-4 analyze-btn"
          :disabled="isAnalyzing"
          @click="startAnalysis"
        >
          <i class="bi bi-cpu me-2"></i>
          {{ isAnalyzing ? 'Analyzing...' : 'Analyze with Agentic AI' }}
        </button>
      </div>
    </div>

    <!-- Progress Bar -->
    <div v-if="isAnalyzing" class="card p-4 mb-4">
      <h6 class="fw-semibold mb-3">AI Analysis in Progress</h6>
      <div class="progress" style="height: 20px;">
        <div
          class="progress-bar progress-bar-striped progress-bar-animated"
          role="progressbar"
          :style="{ width: progress + '%' }"
        >
          {{ progress }}%
        </div>
      </div>
    </div>

    <!-- Completed -->
    <div
      v-if="isCompleted"
      class="alert alert-success d-flex align-items-center mt-4 shadow-sm"
    >
      <i class="bi bi-check-circle-fill fs-4 me-3"></i>
      <div>
        <strong>Analysis Complete</strong><br />
        All uploaded documents have been successfully analyzed.
      </div>
    </div>

    <!-- Results -->
    <div v-if="results.length" class="card p-4 mt-4">
      <h6 class="fw-semibold mb-3">Analysis Results</h6>
      <div
        v-for="(doc, i) in results"
        :key="i"
        class="border rounded p-3 mb-3 bg-light"
      >
        <div class="d-flex justify-content-between align-items-center mb-2">
          <span class="fw-semibold">{{ doc.name }}</span>
          <span :class="riskBadge(doc.risk)" class="badge">{{ doc.risk }}</span>
        </div>
        <div class="progress" style="height:6px;">
          <div
            class="progress-bar"
            :class="riskBar(doc.risk)"
            :style="{ width: doc.score + '%' }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import FileUpload from '../components/FileUpload.vue'
import { ref } from 'vue'

const uploadedFiles = ref([])
const results = ref([])
const progress = ref(0)
const isAnalyzing = ref(false)
const isCompleted = ref(false)

function handleFiles(files) {
  uploadedFiles.value = files
  isCompleted.value = false
  results.value = []
}

function startAnalysis() {
  if (!uploadedFiles.value.length) return
  isAnalyzing.value = true
  progress.value = 0

  // 🔹 Simulate backend progress
  const interval = setInterval(() => {
    progress.value += Math.floor(Math.random() * 10) + 5
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(interval)
      isAnalyzing.value = false
      isCompleted.value = true

      // 🔹 Mock AI risk scoring
      results.value = uploadedFiles.value.map(f => ({
        name: f.name,
        risk: ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)],
        score: Math.floor(Math.random() * 100)
      }))
    }
  }, 400)
}

function riskBadge(risk) {
  if (risk === 'High') return 'bg-danger'
  if (risk === 'Medium') return 'bg-warning text-dark'
  return 'bg-success'
}
function riskBar(risk) {
  if (risk === 'High') return 'bg-danger'
  if (risk === 'Medium') return 'bg-warning'
  return 'bg-success'
}
</script>

<style scoped>
.analyze-btn {
  border-radius: var(--border-radius);
  background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
  border: none;
  transition: all 0.2s ease;
}
.analyze-btn:hover {
  opacity: 0.9;
  transform: scale(1.02);
}
.progress-bar {
  transition: width 0.3s ease;
}
.alert {
  border-radius: var(--border-radius);
}
</style>
