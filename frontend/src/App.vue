<template>
  <div class="d-flex">
    <Sidebar />
    <div class="flex-grow-1">
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

<style scoped>
main {
  min-height: 100vh;
  background-color: #f8f9fa;
}
</style>

