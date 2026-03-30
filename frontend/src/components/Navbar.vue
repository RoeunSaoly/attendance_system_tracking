<template>
  <nav class="navbar">
    <div class="nav-container">
      <router-link to="/" class="nav-brand">FacePulse Attendance</router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-btn" :class="{ active: route.path === '/' }">Scan</router-link>
        <router-link to="/register" class="nav-btn" :class="{ active: route.path === '/register' }">Register</router-link>
        <router-link to="/records" class="nav-btn" :class="{ active: route.path === '/records' }">Records</router-link>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router';
const route = useRoute();
</script>

<style scoped>
.navbar {
  background: rgba(8, 14, 28, 0.9);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.14);
  padding: 0 28px;
  height: 64px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-brand {
  font-size: 1.4rem;
  font-weight: 700;
  background: linear-gradient(135deg, #00a6fb, #2ec4b6);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  letter-spacing: -0.5px;
  text-decoration: none;
}

.nav-links {
  display: flex;
  gap: 8px;
}

.nav-btn {
  background: transparent;
  border: none;
  color: #e8f3ff;
  padding: 8px 20px;
  font-size: 0.9rem;
  font-weight: 500;
  border-radius: 40px;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
}

.nav-btn:hover {
  background: rgba(0, 166, 251, 0.2);
  color: #8de7ff;
}

.nav-btn.active {
  background: rgba(46, 196, 182, 0.16);
  color: #b6fff6;
  box-shadow: 0 4px 12px rgba(46, 196, 182, 0.2);
}
</style>
