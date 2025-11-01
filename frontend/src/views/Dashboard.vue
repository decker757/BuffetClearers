<template>
  <div>
    <h4 class="mb-4 fw-bold text-primary">Dashboard Overview</h4>

    <div class="row g-3 mb-4">
      <div class="col-md-4"><KpiCard title="Transactions Scanned" :value="1000" trend="up" /></div>
      <div class="col-md-4"><KpiCard title="High-Risk Alerts" :value="32" trend="down" /></div>
      <div class="col-md-4"><KpiCard title="Documents Verified" :value="58" trend="up" /></div>
    </div>

    <div class="card p-4">
      <h6 class="fw-semibold mb-3">Agent Activity</h6>
      <ul class="list-group list-group-flush">
        <li class="list-group-item d-flex justify-content-between">
          <span>Regulation Ingestor</span><span class="badge bg-success">Active</span>
        </li>
        <li class="list-group-item d-flex justify-content-between">
          <span>Transaction Analyzer</span><span class="badge bg-warning text-dark">Running</span>
        </li>
        <li class="list-group-item d-flex justify-content-between">
          <span>Doc Corroborator</span><span class="badge bg-secondary">Idle</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import KpiCard from '../components/KpiCard.vue'
</script>

