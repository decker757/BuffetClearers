<template>
  <div>
    <!-- Hero Strip -->
    <section class="card p-3 mb-4">
      <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
        <div>
          <h4 class="fw-bold m-0">Welcome back, Analyst</h4>
          <div class="text-muted small">Your AI agents are live and monitoring transactions in real-time.</div>
        </div>
        <div class="d-flex align-items-center gap-3">
          <div class="badge bg-success">Agents Active: 3</div>
          <div class="badge bg-warning text-dark">Open Alerts: 32</div>
          <button class="btn btn-primary btn-sm">Sync Now</button>
        </div>
      </div>
    </section>

    <!-- KPI row -->
    <section class="row g-3 mb-3">
      <div class="col-md-4"><KpiCard title="Transactions Scanned" :value="1000" trend="up" :series="[200,260,240,310,380,420,500]" /></div>
      <div class="col-md-4"><KpiCard title="High-Risk Alerts" :value="32" trend="down" :series="[60,54,49,42,39,36,32]" /></div>
      <div class="col-md-4"><KpiCard title="Documents Verified" :value="58" trend="up" :series="[10,14,17,25,31,46,58]" /></div>
    </section>

    <!-- Risk Donut -->
    <section class="card p-3 mb-4">
      <h6 class="fw-semibold mb-2">Risk Distribution</h6>
      <RiskDonut :series="[32,18,50]" />
    </section>
  </div>
</template>

<script setup>
import KpiCard from '../components/KpiCard.vue'
import RiskDonut from '../components/RiskDonut.vue'
</script>
