<template>
  <div
    class="upload-box border rounded p-4 text-center bg-light shadow-sm"
    style="border-style: dashed; cursor: pointer;"
    @click="openPicker"
  >
    <input
      type="file"
      multiple
      ref="fileInput"
      hidden
      @change="handleFiles"
    />

    <i class="bi bi-upload fs-3 text-primary"></i>
    <p class="mb-1 fw-semibold">Upload Documents</p>
    <p class="text-muted small mb-0">Click to select or drop files here</p>

    <ul
      v-if="selectedFiles.length"
      class="list-group list-group-flush mt-3 text-start"
    >
      <li
        v-for="(file, index) in selectedFiles"
        :key="index"
        class="list-group-item d-flex justify-content-between align-items-center"
      >
        <span>{{ file.name }}</span>
        <span class="badge bg-secondary">
          {{ (file.size / 1024).toFixed(1) }} KB
        </span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const fileInput = ref(null)
const selectedFiles = ref([])
const emit = defineEmits(['files-selected'])

function openPicker() {
  fileInput.value.click()
}

function handleFiles(e) {
  selectedFiles.value = Array.from(e.target.files)
  console.log('FileUpload emitting:', selectedFiles.value)
  emit('files-selected', selectedFiles.value) // ✅ tell parent
}
</script>

<style scoped>
.upload-box:hover {
  background-color: #f8f9fa;
  transition: background-color 0.2s ease;
}
</style>
