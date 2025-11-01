<template>
  <nav class="sidebar vh-100 d-flex flex-column p-3" style="width:260px" aria-label="Primary">
    <div class="d-flex align-items-center gap-2 mb-4">
      <i class="bi bi-bank2 fs-4 text-primary"></i>
      <h5 class="m-0 fw-bold">AML Agentic AI</h5>
    </div>

    <ul class="nav nav-pills flex-column gap-1" role="menu">
      <li><RouterLink :class="linkClass('/')" to="/" role="menuitem">
        <i class="bi bi-speedometer2 me-2"></i>Dashboard
      </RouterLink></li>
      <li><RouterLink :class="linkClass('/monitoring')" to="/monitoring" role="menuitem">
        <i class="bi bi-activity me-2"></i>Monitoring
      </RouterLink></li>
      <li><RouterLink :class="linkClass('/documents')" to="/documents" role="menuitem">
        <i class="bi bi-file-earmark-text me-2"></i>Documents
      </RouterLink></li>
      <li><RouterLink :class="linkClass('/reports')" to="/reports" role="menuitem">
        <i class="bi bi-bar-chart-line me-2"></i>Reports
      </RouterLink></li>
    </ul>

    <div class="mt-auto small muted pt-3 border-top" style="border-color:var(--border)!important">
      <div>© 2025 Julius Baer Hackathon</div>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'
const route = useRoute()
const linkClass = (path) => [
  'nav-link px-3 py-2 rounded-3',
  route.path === path ? 'active' : ''
]
</script>
