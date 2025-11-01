<template>
  <section class="card p-3" aria-label="Recent alerts">
    <div class="d-flex align-items-center justify-content-between mb-2">
      <h6 class="m-0">Recent Alerts</h6>
      <button class="btn btn-sm btn-outline-secondary">View all</button>
    </div>

    <ul class="list-unstyled m-0">
      <li v-for="(a, i) in items" :key="i" class="d-flex align-items-start justify-content-between py-2 border-bottom">
        <div class="me-3">
          <span :class="badgeClass(a.level)" class="badge me-2" aria-hidden="true">{{ a.level }}</span>
          <span class="fw-semibold">{{ a.title }}</span>
          <div class="text-muted small">{{ a.subtitle }}</div>
        </div>
        <time class="small text-muted" :datetime="a.iso">{{ a.time }}</time>
      </li>
    </ul>
  </section>
</template>

<script setup>
const props = defineProps({ items: { type: Array, default: () => [] } })
const badgeClass = (l) => l === 'High' ? 'bg-danger' : l === 'Medium' ? 'bg-warning text-dark' : 'bg-success'
</script>
