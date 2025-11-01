<template>
  <div class="toast-stack" role="status" aria-live="polite">
    <div v-for="(t,i) in toasts" :key="i" class="card p-3 mb-2" :class="tone(t.tone)">
      <div class="d-flex align-items-start justify-content-between">
        <div>
          <div class="fw-semibold mb-1">{{ t.title }}</div>
          <div class="muted small">{{ t.msg }}</div>
        </div>
        <button class="btn btn-sm btn-outline-light" @click="close(i)" aria-label="Dismiss toast"><i class="bi bi-x"></i></button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
const toasts = reactive([])
function push(t){ toasts.push({ tone:'info', ...t }); setTimeout(()=>toasts.shift(), 4200) }
function close(i){ toasts.splice(i,1) }
function tone(t){ return t==='danger'?'border-danger':t==='success'?'border-success':'border-info' }
defineExpose({ push })
</script>

<style scoped>
.toast-stack{ position: fixed; right: 24px; top: 24px; z-index: 70; width: 360px; }
</style>
