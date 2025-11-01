<template>
  <section class="card p-3" aria-label="Agent status">
    <h6 class="mb-3">Agent Activity</h6>
    <div class="row g-2">
      <div v-for="(agent, i) in agents" :key="i" class="col-md-4">
        <div class="p-3 border rounded-3 d-flex align-items-center justify-content-between">
          <div>
            <div class="fw-semibold">{{ agent.name }}</div>
            <div class="text-muted small">{{ agent.desc }}</div>
          </div>
          <span :class="chip(agent.state)" class="badge">{{ agent.state }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({
  agents: { type: Array, default: () => [] }
})
const chip = (s) => s === 'Active' ? 'bg-success' : s === 'Running' ? 'bg-primary' : s === 'Idle' ? 'bg-secondary' : 'bg-warning text-dark'
</script>
