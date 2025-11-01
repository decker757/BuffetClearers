import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAmlStore = defineStore('aml', () => {
  const transactions = ref([])
  const documents = ref([])
  const alerts = ref([])

  return { transactions, documents, alerts }
})
