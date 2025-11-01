<template>
  <div class="d-flex">
    <Sidebar />
    <div class="flex-grow-1 d-flex flex-column">
      <Topbar />
      <main class="p-4">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Topbar from './components/Topbar.vue'
</script>
