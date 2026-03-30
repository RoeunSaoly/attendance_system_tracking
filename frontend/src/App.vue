<template>
  <Navbar />
  <router-view />
  <Toast :message="toast.message" :visible="toast.visible" :type="toast.type" />
</template>

<script setup>
import Navbar from '@/components/Navbar.vue';
import Toast from '@/components/Toast.vue';
import { useToast } from '@/composables/useToast';
const toast = useToast();
</script>
