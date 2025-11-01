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
console.log('Documents.vue received:', files)
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
  position: relative;
  font-weight: 600;
  border: none;
  color: #fff;
  background: linear-gradient(270deg, #0072ff, #00c6ff);
  background-size: 200% 200%;
  border-radius: 0.75rem;
  box-shadow: 0 0 10px rgba(0, 114, 255, 0.4);
  transition: all 0.3s ease;
  animation: gradientShift 3s ease infinite;
}

.analyze-btn:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 0 20px rgba(0, 183, 255, 0.6);
}

.analyze-btn:disabled {
  background: linear-gradient(270deg, #6c757d, #adb5bd);
  box-shadow: none;
  opacity: 0.8;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

/* Progress bar glow while analyzing */
.progress-bar-animated {
  animation: progressPulse 1.5s infinite;
}

@keyframes progressPulse {
  0% { box-shadow: 0 0 5px rgba(0,183,255,0.4); }
  50% { box-shadow: 0 0 15px rgba(0,183,255,0.8); }
  100% { box-shadow: 0 0 5px rgba(0,183,255,0.4); }
}

/* Success alert animation */
.alert-success {
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

