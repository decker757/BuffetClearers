<template>
  <header class="bg-white border-bottom shadow-sm py-2 px-4 d-flex justify-content-between align-items-center">
    <h6 class="m-0 fw-semibold text-primary">Real-Time AML Monitoring Platform</h6>
    <div class="text-muted small">
      Last Synced: <span class="fw-semibold">{{ lastSync }}</span>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const lastSync = ref('')
onMounted(() => {
  const now = new Date()
  lastSync.value = now.toLocaleTimeString('en-SG', { hour: '2-digit', minute: '2-digit' })
})
</script>

