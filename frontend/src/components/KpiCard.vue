<template>
  <div class="card text-center py-3">
    <div class="card-body">
      <h6 class="text-muted mb-2">{{ title }}</h6>
      <h3 class="fw-bold mb-1">{{ value.toLocaleString() }}</h3>
      <span :class="trendClass">
        <i :class="iconClass"></i>
        {{ trendText }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  value: Number,
  trend: String // "up" | "down"
})

const trendClass = computed(() =>
  props.trend === 'up' ? 'text-success small' : 'text-danger small'
)
const iconClass = computed(() =>
  props.trend === 'up' ? 'bi bi-arrow-up' : 'bi bi-arrow-down'
)
const trendText = computed(() =>
  props.trend === 'up' ? 'Up from last week' : 'Down from last week'
)
</script>

<style scoped>
.card:hover {
  transform: translateY(-2px);
  transition: 0.2s ease;
}
</style>

