<template>
  <div class="page">
    <div class="page-header">
      <h2 class="gradient-text">Live Face Scanner</h2>
      <p class="subtitle">Real-time recognition with auto attendance marking.</p>
    </div>

    <div class="stats">
      <StatCard icon="ALL" :value="store.stats.total" label="Students" />
      <StatCard icon="IN" :value="store.stats.todayTotal" label="Checked Today" color="green" />
      <StatCard icon="OK" :value="store.stats.ontime" label="On Time" color="orange" />
      <StatCard icon="LATE" :value="store.stats.late" label="Late" color="red" />
    </div>

    <div class="scan-layout">
      <div class="card camera-card">
        <div class="card-header">
          <span class="time-rule">On time: 08:00 | Late: after 08:30</span>
          <span v-if="isCameraActive" class="live-badge">LIVE</span>
        </div>

        <div class="camera-wrapper">
          <video ref="cameraVideo" class="camera-feed" playsinline muted autoplay></video>
          <canvas ref="canvas" class="overlay-canvas" width="640" height="480"></canvas>

          <div v-if="!isCameraActive" class="camera-placeholder">
            <div class="placeholder-icon">CAM</div>
            <p>Tap Start Camera to begin scanning</p>
          </div>
        </div>

        <div class="camera-controls">
          <div class="btn-group">
            <button @click="startCamera" :disabled="isCameraActive" class="btn btn-primary">
              Start Camera
            </button>
            <button @click="stopCamera" :disabled="!isCameraActive" class="btn btn-danger">
              Stop Camera
            </button>
          </div>
          <div class="scan-status">{{ scanStatus }}</div>
        </div>
      </div>

      <div class="card log-card">
        <div class="card-header">
          <span class="card-title">Recognition Log</span>
          <button @click="store.clearLogs()" class="btn btn-sm btn-outline">Clear</button>
        </div>

        <div class="log">
          <div v-if="store.logs.length === 0" class="empty-log">No scans yet. Start the camera to begin.</div>

          <div v-for="(log, idx) in store.logs" :key="idx" class="log-item" :class="log.type">
            <div class="log-top">
              <div>
                <span class="log-name">{{ log.name }}</span>
                <span v-if="log.class" class="log-class"> - {{ log.class }}</span>
              </div>
              <span class="log-status" :class="log.type">{{ log.status }}</span>
            </div>
            <div class="log-meta">
              <span>{{ log.time }}</span>
              <span v-if="typeof log.score === 'number'">Score {{ log.score.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { useAttendanceStore } from '@/stores/attendance';
import StatCard from '@/components/StatCard.vue';
import { useCamera } from '@/composables/useCamera';
import { useToast } from '@/composables/useToast';

const store = useAttendanceStore();
const toast = useToast();

const { video, isActive: isCameraActive, start: startCam, stop: stopCam, setVideoRef } = useCamera();

const canvas = ref(null);
const cameraVideo = ref(null);
const scanStatus = ref('Idle');

let detectInterval = null;
let markInterval = null;
let animationId = null;
let currentFaces = [];

const clearLoops = () => {
  if (detectInterval) clearInterval(detectInterval);
  if (markInterval) clearInterval(markInterval);
  if (animationId) cancelAnimationFrame(animationId);

  detectInterval = null;
  markInterval = null;
  animationId = null;
};

const drawFrame = () => {
  if (!isCameraActive.value || !canvas.value || !video.value) return;

  const ctx = canvas.value.getContext('2d');
  const source = video.value;

  if (!source || source.videoWidth === 0 || source.videoHeight === 0) {
    animationId = requestAnimationFrame(drawFrame);
    return;
  }

  canvas.value.width = source.videoWidth;
  canvas.value.height = source.videoHeight;
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);

  for (const face of currentFaces) {
    const [x, y, w, h] = face.bbox;

    let color = '#ffd166';
    let label = 'Unknown';

    if (face.recognized) {
      if (face.already_marked) {
        color = '#5bc0eb';
        label = `${face.name} (already)`;
      } else {
        color = '#2ec4b6';
        label = face.name;
      }
    }

    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);

    ctx.font = 'bold 15px ui-sans-serif';
    ctx.fillStyle = color;
    ctx.fillText(label, x + 4, Math.max(14, y - 6));
  }

  animationId = requestAnimationFrame(drawFrame);
};

const captureFrame = (quality = 0.75) => {
  if (!canvas.value || !video.value) return null;
  if (video.value.videoWidth === 0 || video.value.videoHeight === 0) return null;

  const tmp = document.createElement('canvas');
  tmp.width = video.value.videoWidth;
  tmp.height = video.value.videoHeight;
  tmp.getContext('2d').drawImage(video.value, 0, 0);
  return tmp.toDataURL('image/jpeg', quality);
};

const startCamera = async () => {
  if (isCameraActive.value) return;

  try {
    await startCam();

    if (!cameraVideo.value || !video.value) {
      throw new Error('Camera video element is not ready.');
    }

    clearLoops();
    currentFaces = [];
    scanStatus.value = 'Scanning...';

    drawFrame();

    detectInterval = setInterval(async () => {
      if (!isCameraActive.value) return;
      const frame = captureFrame(0.6);
      if (!frame) return;

      const faces = await store.detectFaces(frame);
      currentFaces = faces;
      if (faces.length === 0) {
        scanStatus.value = 'Scanning...';
      } else {
        const recognizedCount = faces.filter(face => face.recognized).length;
        const unknownCount = faces.length - recognizedCount;
        scanStatus.value = `${faces.length} face(s): ${recognizedCount} match, ${unknownCount} unknown`;
      }
    }, 450);

    markInterval = setInterval(async () => {
      if (!isCameraActive.value) return;
      const frame = captureFrame(0.82);
      if (!frame) return;
      const result = await store.markAttendance(frame);

      if (!result?.success && result?.message) {
        scanStatus.value = result.message;
      }

      if ((result?.processed || 0) === 0 && currentFaces.length > 0) {
        store.addDetectionLogs(currentFaces);
      }
    }, 2200);
  } catch (e) {
    toast.show(e.message || 'Unable to start camera.', true);
    stopCamera();
  }
};

const stopCamera = () => {
  stopCam();
  clearLoops();

  currentFaces = [];
  scanStatus.value = 'Idle';

  const ctx = canvas.value?.getContext('2d');
  if (ctx && canvas.value) {
    ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);
  }
};

onMounted(() => {
  setVideoRef(cameraVideo.value);
  store.fetchStats();
});

onUnmounted(() => {
  stopCamera();
});
</script>

<style scoped>
.page {
  padding: 28px;
  max-width: 1400px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.page-header {
  margin-bottom: 28px;
}

.gradient-text {
  font-size: 1.8rem;
  font-weight: 700;
  background: linear-gradient(135deg, #00a6fb, #2ec4b6);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.subtitle {
  color: #d9e8fb;
  font-size: 0.9rem;
  margin-top: 6px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  margin-bottom: 28px;
}

.scan-layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 24px;
}

.card {
  background: rgba(17, 23, 40, 0.82);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.18);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 700;
  color: #7ae0ff;
}

.time-rule {
  font-size: 0.74rem;
  color: #bed2ec;
}

.camera-wrapper {
  position: relative;
  background: rgba(2, 5, 15, 0.7);
  border-radius: 20px;
  overflow: hidden;
  aspect-ratio: 4 / 3;
}

.camera-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: #000;
}

.overlay-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  display: block;
}

.camera-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(3, 8, 18, 0.65);
  backdrop-filter: blur(4px);
}

.placeholder-icon {
  width: 56px;
  height: 56px;
  border-radius: 999px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 166, 251, 0.2);
  color: #8de7ff;
  font-weight: 700;
  margin-bottom: 10px;
}

.camera-placeholder p {
  color: #d7e6fb;
  font-size: 0.9rem;
}

.live-badge {
  background: #ff4d6d;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 1px;
  color: #380713;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.72;
    transform: scale(0.98);
  }
}

.camera-controls {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  align-items: center;
}

.btn-group {
  display: flex;
  gap: 10px;
}

.scan-status {
  margin-left: auto;
  background: rgba(4, 10, 22, 0.72);
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 0.77rem;
  color: #dce9fb;
}

.log-card {
  display: flex;
  flex-direction: column;
  height: 500px;
}

.log {
  flex: 1;
  overflow-y: auto;
  padding-right: 4px;
}

.empty-log {
  text-align: center;
  color: #b9cde8;
  padding: 32px 0;
}

.log-item {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 8px;
  border-left: 4px solid #7ae0ff;
}

.log-item.ontime {
  border-left-color: #2ec4b6;
  background: rgba(46, 196, 182, 0.1);
}

.log-item.late {
  border-left-color: #ffd166;
  background: rgba(255, 209, 102, 0.12);
}

.log-item.unknown {
  border-left-color: #ff7a93;
  background: rgba(255, 122, 147, 0.14);
}

.log-item.detected {
  border-left-color: #7ae0ff;
  background: rgba(122, 224, 255, 0.12);
}

.log-item.already {
  border-left-color: #5bc0eb;
  background: rgba(91, 192, 235, 0.12);
  opacity: 0.8;
}

.log-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 8px;
}

.log-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 0.72rem;
  color: #bad0ea;
}

.log-name {
  font-weight: 600;
  color: #f4f9ff;
}

.log-class {
  font-size: 0.75rem;
  color: #bed2ec;
}

.log-status {
  font-size: 0.7rem;
  color: #d1e1f7;
  font-family: monospace;
  border-radius: 999px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.08);
}

.log-status.ontime {
  color: #2ec4b6;
}

.log-status.late {
  color: #ffd166;
}

.log-status.already {
  color: #5bc0eb;
}

.log-status.unknown {
  color: #ff9cb0;
}

.log-status.detected {
  color: #7ae0ff;
}

.btn {
  padding: 8px 18px;
  border-radius: 999px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.85rem;
}

.btn-sm {
  padding: 6px 14px;
  font-size: 0.76rem;
}

.btn-primary {
  background: #00a6fb;
  color: #06233a;
}

.btn-primary:hover {
  background: #55c9ff;
  transform: translateY(-1px);
}

.btn-danger {
  background: #ff4d6d;
  color: #3b0915;
}

.btn-danger:hover {
  background: #ff7090;
  transform: translateY(-1px);
}

.btn-outline {
  background: transparent;
  border: 1px solid rgba(122, 224, 255, 0.6);
  color: #dff0ff;
}

.btn-outline:hover {
  background: rgba(122, 224, 255, 0.12);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

@media (max-width: 900px) {
  .scan-layout {
    grid-template-columns: 1fr;
  }

  .stats {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 600px) {
  .stats {
    grid-template-columns: 1fr;
  }

  .log-top,
  .log-meta {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
