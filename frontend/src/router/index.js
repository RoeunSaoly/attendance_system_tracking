import { createRouter, createWebHistory } from 'vue-router';
import ScanView from '@/views/ScanView.vue';
import RegisterView from '@/views/RegisterView.vue';
import RecordsView from '@/views/RecordsView.vue';

const routes = [
  { path: '/', name: 'scan', component: ScanView },
  { path: '/register', name: 'register', component: RegisterView },
  { path: '/records', name: 'records', component: RecordsView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;