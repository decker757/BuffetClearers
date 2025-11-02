<template>
  <div>
    <!-- Header -->
    <section class="card p-3 mb-4">
      <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h4 class="fw-bold m-0">Real-Time AML Monitoring</h4>
          <div class="text-muted small">Upload your transaction CSV and view results directly from the backend.</div>
        </div>
      </div>
    </section>

    <!-- Upload + Analyze -->
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
        :disabled="!fileData || analyzing"
        @click="analyze"
      >
        <i class="bi bi-cpu me-2"></i>
        {{ analyzing ? 'Analyzing…' : 'Analyze Transactions' }}
      </button>

      <div v-if="analyzing" class="mt-3">
        <div class="progress" style="height: 10px;">
          <div
            class="progress-bar progress-bar-striped progress-bar-animated"
            :style="{ width: progress + '%' }"
          ></div>
        </div>
        <small class="text-muted">Processing file on backend...</small>
      </div>
    </section>

    <!-- Results Table -->
    <section v-if="results.length" class="card p-4">
      <h6 class="fw-semibold mb-3">Backend Output</h6>
      <div class="table-responsive">
        <table class="table table-hover align-middle">
          <thead class="table-light">
            <tr>
              <th v-for="(key, i) in Object.keys(results[0])" :key="i">
                {{ key }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in results" :key="i">
              <td v-for="(value, k) in row" :key="k">{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const fileInput = ref(null)
const fileName = ref('')
const fileData = ref(null)
const results = ref([])
const analyzing = ref(false)
const progress = ref(0)

function handleFile(e) {
  const file = e.target.files[0]
  if (!file) return
  fileName.value = file.name
  fileData.value = file
}

async function analyze() {
  if (!fileData.value) return
  analyzing.value = true
  progress.value = 20
  results.value = []

  try {
    const formData = new FormData()
    formData.append('file', fileData.value)

    const response = await axios.post('http://127.0.0.1:5000/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        progress.value = Math.min(80, Math.round((event.loaded / event.total) * 80))
      },
    })

    progress.value = 100
    results.value = response.data.results || response.data || []

  } catch (err) {
    console.error('Error analyzing file:', err)
    alert('Error connecting to backend. Check your Python server.')
  } finally {
    analyzing.value = false
  }
}
</script>
