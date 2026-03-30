<template>
  <div class="toast" :class="[type, { show: visible }]">
    {{ message }}
  </div>
</template>

<script setup>
defineProps({
  message: String,
  visible: Boolean,
  type: {
    type: String,
    default: 'info'
  }
});
</script>

<style scoped>
.toast {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  padding: 12px 24px;
  border-radius: 60px;
  color: #1a1a2e;
  font-size: 0.85rem;
  border-left: 4px solid #4fc3f7;
  transform: translateY(20px);
  opacity: 0;
  transition: 0.2s;
  pointer-events: none;
  z-index: 200;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.toast.error {
  border-left-color: #ff4d6d;
}

.toast.success {
  border-left-color: #2ec4b6;
}

.toast.show {
  transform: translateY(0);
  opacity: 1;
}
</style>
