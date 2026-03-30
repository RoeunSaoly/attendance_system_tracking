<template>
  <div class="stat-card">
    <div class="stat-icon" :style="{ backgroundColor: bgColor }">
      {{ icon }}
    </div>
    <div>
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  icon: String,
  value: [String, Number],
  label: String,
  color: { type: String, default: 'primary' }
});

const bgColor = computed(() => {
  const colors = {
    primary: 'rgba(0, 166, 251, 0.18)',
    green: 'rgba(46, 196, 182, 0.2)',
    orange: 'rgba(255, 209, 102, 0.2)',
    red: 'rgba(255, 77, 109, 0.2)'
  };
  return colors[props.color] || colors.primary;
});
</script>

<style scoped>
.stat-card {
  background: rgba(17, 23, 40, 0.82);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 18px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  transition: all 0.2s;
}

.stat-card:hover {
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.18);
  transform: translateY(-2px);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.4px;
  color: #dff0ff;
}

.stat-value {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
  color: #f8fcff;
}

.stat-label {
  font-size: 0.75rem;
  color: #c0d2eb;
  text-transform: uppercase;
  letter-spacing: 0.7px;
}
</style>
