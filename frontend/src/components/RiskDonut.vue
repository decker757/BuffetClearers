<template>
  <apexchart type="donut" height="260" :options="opts" :series="series"></apexchart>
</template>

<script setup>
import ApexChart from 'vue3-apexcharts'
defineProps({ series:{ type:Array, default:()=>[32,18,50] } })
const opts = {
  labels:['High','Medium','Low'],
  legend:{ labels:{ colors:'#212529' } },
  dataLabels:{ enabled:false },
  colors:['#ff4d6d','#ffd166','#19c37d'],
  stroke:{ colors:['#ffffff'] },
  chart:{ background:'transparent', foreColor:'#212529' }
}
</script>

<script>
export default { components:{ apexchart:ApexChart } }
</script>
