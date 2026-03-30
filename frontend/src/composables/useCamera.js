import { ref, onUnmounted } from 'vue';

export function useCamera() {
  const stream = ref(null);
  const video = ref(null);
  const isActive = ref(false);

  const waitForVideoReady = (el) =>
    new Promise((resolve) => {
      if (!el) {
        resolve();
        return;
      }

      if (el.readyState >= 2 && el.videoWidth > 0 && el.videoHeight > 0) {
        resolve();
        return;
      }

      let resolved = false;
      const done = () => {
        if (resolved) return;
        resolved = true;
        el.removeEventListener('loadedmetadata', done);
        el.removeEventListener('loadeddata', done);
        resolve();
      };

      el.addEventListener('loadedmetadata', done, { once: true });
      el.addEventListener('loadeddata', done, { once: true });
      setTimeout(done, 1200);
    });

  const setVideoRef = (el) => {
    video.value = el;
    if (el && stream.value) {
      el.srcObject = stream.value;
      el.play?.().catch(() => {});
    }
  };

  const start = async () => {
    if (stream.value) await stop();
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
      });
      stream.value = mediaStream;
      if (video.value) {
        video.value.srcObject = mediaStream;
        await video.value.play?.();
        await waitForVideoReady(video.value);
      }
      isActive.value = true;
    } catch (err) {
      console.error('Camera error:', err);
      throw err;
    }
  };

  const stop = async () => {
    if (stream.value) {
      stream.value.getTracks().forEach(track => track.stop());
      stream.value = null;
    }
    if (video.value) video.value.srcObject = null;
    isActive.value = false;
  };

  onUnmounted(stop);

  return { stream, video, isActive, start, stop, setVideoRef };
}
