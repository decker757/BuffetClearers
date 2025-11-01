<template>
  <button class="ai-pulse" :class="{running}" @click="$emit('openAgentLog')" aria-label="Open AI Agent Activity">
    <i class="bi bi-cpu" aria-hidden="true"></i>
  </button>
</template>

<script setup>
defineProps({ running:{type:Boolean, default:false} })
</script>

<style scoped>
.ai-pulse{
  position: fixed; right: 24px; bottom: 24px;
  width: 54px; height: 54px; border-radius: 50%;
  background: radial-gradient(circle at 30% 30%, #27d3ff, #0aa8ff);
  color:#051529; border: none; box-shadow: 0 10px 30px rgba(0,168,255,.4);
  display:flex; align-items:center; justify-content:center;
  transition: transform .15s ease, box-shadow .2s ease; z-index: 60;
}
.ai-pulse:hover{ transform: translateY(-2px) scale(1.03); box-shadow: 0 16px 40px rgba(0,168,255,.55) }
.running::after{
  content:''; position:absolute; inset:-8px; border-radius:50%;
  box-shadow: 0 0 0 0 rgba(39,211,255,.45);
  animation: pulse 1.6s infinite;
}
@keyframes pulse{ 0%{box-shadow:0 0 0 0 rgba(39,211,255,.45)} 70%{box-shadow:0 0 0 16px rgba(39,211,255,0)} 100%{box-shadow:0 0 0 0 rgba(39,211,255,0)} }
</style>
