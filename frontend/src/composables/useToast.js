import { ref } from 'vue';

const message = ref('');
const visible = ref(false);
const type = ref('info');
let timeout = null;

export function useToast() {
  const show = (msg, options = {}) => {
    let nextDuration = 2800;
    let nextType = 'info';

    if (typeof options === 'boolean') {
      nextType = options ? 'error' : 'info';
    } else if (typeof options === 'number') {
      nextDuration = options;
    } else if (options && typeof options === 'object') {
      if (typeof options.duration === 'number') {
        nextDuration = options.duration;
      }
      if (options.type === 'success' || options.type === 'error' || options.type === 'info') {
        nextType = options.type;
      } else if (options.error === true) {
        nextType = 'error';
      }
    }

    message.value = msg || '';
    type.value = nextType;
    visible.value = true;
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => {
      visible.value = false;
    }, nextDuration);
  };
  return { message, visible, type, show };
}
