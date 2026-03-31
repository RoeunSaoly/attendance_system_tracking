import Swal from 'sweetalert2';

const resolveToastConfig = (options) => {
  let duration = 2800;
  let type = 'info';

  if (typeof options === 'boolean') {
    type = options ? 'error' : 'info';
  } else if (typeof options === 'number') {
    duration = options;
  } else if (options && typeof options === 'object') {
    if (typeof options.duration === 'number') {
      duration = options.duration;
    }
    if (options.type === 'success' || options.type === 'error' || options.type === 'info') {
      type = options.type;
    } else if (options.error === true) {
      type = 'error';
    }
  }

  return { duration, type };
};

export function useToast() {
  const show = (msg, options = {}) => {
    const { duration, type } = resolveToastConfig(options);

    return Swal.fire({
      toast: true,
      position: 'top-end',
      icon: type,
      title: msg || '',
      showConfirmButton: false,
      timer: duration,
      timerProgressBar: true,
      didOpen: (popup) => {
        popup.addEventListener('mouseenter', Swal.stopTimer);
        popup.addEventListener('mouseleave', Swal.resumeTimer);
      },
    });
  };

  return { show };
}
