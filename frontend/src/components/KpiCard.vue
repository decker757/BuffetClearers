<template>
  <article class="card p-3 h-100">
    <div class="d-flex align-items-center justify-content-between">
      <div>
        <h6 class="muted mb-1">{{ title }}</h6>
        <div class="h3 m-0 fw-bold">{{ formatted }}</div>
      </div>
      <span :class="pill" class="px-2 py-1 rounded-3 small d-inline-flex align-items-center gap-1">
        <i :class="icon"></i>{{ trendText }}
      </span>
    </div>
    <svg viewBox="0 0 100 28" class="mt-2" width="100%" height="28">
      <polyline :points="points" fill="none" stroke-width="2" stroke-linecap="round" />
    </svg>
  </article>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  title:String, value:[Number,String], trend:{type:String,default:'flat'},
  series:{type:Array,default:()=>[12,14,13,18,17,22,25]}
})
const formatted = computed(()=> typeof props.value==='number'? props.value.toLocaleString(): props.value)
const pill = computed(()=> props.trend==='up'?'bg-success text-dark':'bg-danger text-light')
const icon = computed(()=> props.trend==='up'?'bi bi-arrow-up':'bi bi-arrow-down')
const trendText = computed(()=> props.trend==='up'?'Up':'Down')
const points = computed(()=>{
  const s = props.series; if(!s.length) return ''
  const min = Math.min(...s), max = Math.max(...s), span = Math.max(1,max-min)
  return s.map((v,i)=>`${(i/(s.length-1))*100},${28-((v-min)/span)*24-2}`).join(' ')
})
</script>
