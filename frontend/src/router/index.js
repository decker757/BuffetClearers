import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Monitoring from '../views/Monitoring.vue'
import Documents from '../views/Documents.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: Dashboard },
  { path: '/monitoring', name: 'Monitoring', component: Monitoring },
  { path: '/documents', name: 'Documents', component: Documents }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
