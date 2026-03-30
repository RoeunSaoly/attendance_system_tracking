<template>
  <div class="page">
    <div class="page-header">
      <h2>Create Student Profile</h2>
      <p class="subtitle">Capture 1-3 angles so recognition stays accurate.</p>
    </div>

    <div class="register-layout">
      <div class="card">
        <h3 class="section-title">Student Details</h3>

        <div class="form-group">
          <label>Student ID *</label>
          <input v-model="form.id" type="text" placeholder="e.g. ST004" />
        </div>

        <div class="form-group">
          <label>Full Name *</label>
          <input v-model="form.name" type="text" placeholder="e.g. Alex Nguyen" />
        </div>

        <div class="form-group">
          <label>Class</label>
          <input v-model="form.class" type="text" placeholder="e.g. 11A" />
        </div>

        <h3 class="section-title mt-6">Face Photos *</h3>
        <div class="photo-slots">
          <div v-for="(slot, idx) in photoSlots" :key="idx" class="photo-slot" :class="{ filled: slot }">
            <div class="slot-label">{{ captureLabels[idx] || `Extra ${idx - 2}` }}</div>
            <div class="slot-preview">
              <img v-if="slot" :src="slot" class="slot-image" alt="Student preview" />
              <span v-else class="slot-empty">No photo</span>
            </div>
            <button @click="captureToSlot(idx)" :disabled="!regCamActive" class="btn btn-sm btn-blue">
              Capture
            </button>
          </div>
        </div>

        <div class="upload-section">
          <label class="file-upload-btn">
            Upload Photos
            <input type="file" accept="image/*" multiple @change="handleUpload" class="hidden-input" />
          </label>

          <input
            type="text"
            v-model="imageUrl"
            placeholder="Paste an image URL"
            class="link-input"
          />

          <button @click="handleUrlUpload" class="btn btn-sm btn-blue">Add by Link</button>
          <span class="photo-count">{{ photoCount }} photo(s) added</span>
        </div>

        <button @click="register" class="btn btn-lg btn-green full-width">Save Student</button>
      </div>

      <div class="card">
        <h3 class="section-title">Camera Preview</h3>
        <video ref="regVideo" autoplay muted playsinline class="camera-preview"></video>
        <div class="camera-btns">
          <button @click="startRegCam" class="btn btn-blue">Start Camera</button>
          <button @click="stopRegCam" class="btn btn-red">Stop</button>
        </div>
      </div>
    </div>

    <div class="card mt-6">
      <div class="card-header">
        <h3 class="section-title">Registered Students ({{ store.students.length }})</h3>
      </div>

      <div class="students">
        <div v-for="student in store.students" :key="student.id" class="student-card">
          <span class="student-avatar">{{ student.name?.charAt(0)?.toUpperCase() || '?' }}</span>
          <span class="student-info">
            <span class="student-name">{{ student.name }}</span>
            <span class="student-id">{{ student.id }} {{ student.class ? '- ' + student.class : '' }}</span>
          </span>
          <button @click="store.deleteStudent(student.id, student.name)" class="delete-btn">X</button>
        </div>

        <div v-if="store.students.length === 0" class="empty-state">No students registered yet.</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue';
import { useAttendanceStore } from '@/stores/attendance';
import { useToast } from '@/composables/useToast';

const store = useAttendanceStore();
const toast = useToast();

const form = reactive({ id: '', name: '', class: '' });
const captureLabels = ['Front Face', 'Left Side', 'Right Side'];
const photoSlots = ref([null, null, null]);
const imageUrl = ref('');

const regVideo = ref(null);
const regCamActive = ref(false);
let regStream = null;

const photoCount = computed(() => photoSlots.value.filter(Boolean).length);

const fileToDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Failed to read image file.'));
    reader.readAsDataURL(file);
  });

const pushPhotoToNextSlot = (dataUrl) => {
  const emptyIndex = photoSlots.value.findIndex((slot) => slot === null);
  if (emptyIndex >= 0) {
    photoSlots.value[emptyIndex] = dataUrl;
  } else {
    photoSlots.value.push(dataUrl);
  }
};

const startRegCam = async () => {
  if (regStream) stopRegCam();

  try {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('Camera is not available in this browser.');
    }

    regStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' }
    });

    if (regVideo.value) {
      regVideo.value.srcObject = regStream;
      await regVideo.value.play();
    }

    regCamActive.value = true;
  } catch (e) {
    toast.show(e.message || 'Unable to access camera.', true);
  }
};

const stopRegCam = () => {
  if (regStream) {
    regStream.getTracks().forEach((track) => track.stop());
  }

  regStream = null;
  regCamActive.value = false;

  if (regVideo.value) {
    regVideo.value.srcObject = null;
  }
};

const captureToSlot = (idx) => {
  if (!regCamActive.value || !regVideo.value || regVideo.value.videoWidth === 0) {
    toast.show('Start the camera first.');
    return;
  }

  const canvas = document.createElement('canvas');
  canvas.width = regVideo.value.videoWidth;
  canvas.height = regVideo.value.videoHeight;
  canvas.getContext('2d').drawImage(regVideo.value, 0, 0);
  photoSlots.value[idx] = canvas.toDataURL('image/jpeg', 0.9);

  toast.show(`Photo saved to slot ${idx + 1}`);
};

const handleUpload = async (event) => {
  const files = Array.from(event.target.files || []);

  try {
    for (const file of files) {
      if (!file.type.startsWith('image/')) continue;
      const dataUrl = await fileToDataUrl(file);
      pushPhotoToNextSlot(dataUrl);
    }
  } catch (e) {
    toast.show(e.message || 'Some files could not be loaded.', true);
  } finally {
    event.target.value = '';
  }
};

const handleUrlUpload = async () => {
  const url = imageUrl.value.trim();
  if (!url) {
    toast.show('Paste an image URL first.');
    return;
  }

  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Could not download that image URL.');
    }

    const blob = await response.blob();
    if (!blob.type.startsWith('image/')) {
      throw new Error('The link does not point to an image file.');
    }

    const dataUrl = await fileToDataUrl(blob);
    pushPhotoToNextSlot(dataUrl);
    imageUrl.value = '';
    toast.show('Image added from link.');
  } catch (e) {
    toast.show(e.message || 'Unable to load that image link.', true);
  }
};

const register = async () => {
  const photos = photoSlots.value.filter(Boolean);

  if (!form.id.trim() || !form.name.trim() || photos.length === 0) {
    toast.show('Please enter ID, name, and at least one face photo.');
    return;
  }

  try {
    const result = await store.registerStudent({
      id: form.id.trim(),
      name: form.name.trim(),
      class: form.class.trim(),
      photos
    });

    if (!result?.success) return;

    form.id = '';
    form.name = '';
    form.class = '';
    imageUrl.value = '';
    photoSlots.value = [null, null, null];
  } catch {
    // Error toast is already handled in the store.
  }
};

onMounted(() => {
  store.fetchStudents();
});

onUnmounted(() => {
  stopRegCam();
});
</script>

<style scoped>
.page {
  padding: 28px;
  max-width: 1400px;
  margin: 0 auto;
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

.page-header h2 {
  font-size: 1.8rem;
  font-weight: 700;
  background: linear-gradient(135deg, #0f9fff, #06d6a0);
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
}

.subtitle {
  color: #f5f9ff;
  font-size: 0.9rem;
  margin-top: 6px;
}

.register-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  margin-bottom: 12px;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #f9fdff;
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}

label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #9fb2cf;
  margin-bottom: 6px;
  display: block;
}

input {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  padding: 10px 16px;
  color: #f4f8ff;
  width: 100%;
  transition: 0.2s;
  box-sizing: border-box;
}

input:focus {
  outline: none;
  border-color: #2ec4b6;
  box-shadow: 0 0 0 2px rgba(46, 196, 182, 0.2);
}

input::placeholder {
  color: #90a4c0;
}

.photo-slots {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin: 16px 0;
}

.photo-slot {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 18px;
  padding: 12px;
  text-align: center;
  border: 1px dashed rgba(255, 255, 255, 0.28);
  transition: 0.2s;
}

.photo-slot.filled {
  border-color: #2ec4b6;
  border-style: solid;
}

.slot-label {
  font-size: 0.75rem;
  color: #dbe8ff;
  margin-bottom: 8px;
}

.slot-preview {
  aspect-ratio: 1;
  background: rgba(10, 14, 26, 0.7);
  border-radius: 14px;
  margin-bottom: 10px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slot-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.slot-empty {
  color: #8ba0bd;
  font-size: 0.8rem;
}

.upload-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin: 16px 0 18px;
}

.file-upload-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: 999px;
  padding: 10px 16px;
  color: #f4f8ff;
  cursor: pointer;
  font-size: 0.85rem;
}

.file-upload-btn:hover {
  background: rgba(255, 255, 255, 0.16);
}

.hidden-input {
  display: none;
}

.link-input {
  flex: 1;
  min-width: 200px;
}

.photo-count {
  font-size: 0.82rem;
  color: #d3e1f6;
}

.camera-preview {
  width: 100%;
  border-radius: 16px;
  background: #02050f;
  aspect-ratio: 16 / 9;
  object-fit: cover;
}

.camera-btns {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.students {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
}

.student-card {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 999px;
  padding: 8px 14px 8px 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.student-avatar {
  width: 36px;
  height: 36px;
  background: linear-gradient(140deg, #00a6fb, #06d6a0);
  color: #041427;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.student-info {
  display: flex;
  flex-direction: column;
}

.student-name {
  font-weight: 600;
  color: #ffffff;
}

.student-id {
  font-size: 0.75rem;
  color: #c3d4ec;
}

.delete-btn {
  background: rgba(255, 77, 109, 0.15);
  border: 1px solid rgba(255, 77, 109, 0.6);
  color: #ff90a5;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 0.78rem;
}

.delete-btn:hover {
  background: rgba(255, 77, 109, 0.28);
}

.empty-state {
  color: #b9cde8;
  font-size: 0.9rem;
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

.btn-lg {
  padding: 11px 28px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.75rem;
}

.btn-blue {
  background: #00a6fb;
  color: #06233a;
}

.btn-green {
  background: #2ec4b6;
  color: #032a29;
}

.btn-red {
  background: #ff4d6d;
  color: #3b0915;
}

.btn:hover {
  transform: translateY(-2px);
  filter: brightness(1.05);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.full-width {
  width: 100%;
}

.mt-6 {
  margin-top: 24px;
}

@media (max-width: 900px) {
  .register-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .photo-slots {
    grid-template-columns: 1fr;
  }

  .upload-section {
    align-items: stretch;
  }

  .link-input {
    min-width: 0;
  }
}
</style>
