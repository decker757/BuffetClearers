<template>
  <nav class="d-flex flex-column bg-dark text-light vh-100 p-4 shadow-sm" style="width:230px">
    <h5 class="fw-bold mb-4">AML Agentic AI</h5>
    <ul class="nav flex-column">
      <li class="nav-item mb-2">
        <router-link class="nav-link text-light" to="/">Dashboard</router-link>
      </li>
      <li class="nav-item mb-2">
        <router-link class="nav-link text-light" to="/monitoring">Monitoring</router-link>
      </li>
      <li class="nav-item mb-2">
        <router-link class="nav-link text-light" to="/documents">Documents</router-link>
      </li>
    </ul>
    <div class="mt-auto small text-secondary">
      <hr class="border-secondary" />
      <p class="mb-0">© 2025 Julius Baer</p>
    </div>
  </nav>
</template>

<script setup></script>

<style scoped>
.nav-link:hover {
  color: var(--accent-color) !important;
  transition: color 0.2s ease;
}
</style>

