const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:9090'; // Backend server address

/**
 * Generic fetch wrapper with error handling
 */
export const api = async (url, options = {}) => {
  let res;
  try {
    res = await fetch(`${API_BASE}${url}`, options);
  } catch {
    throw new Error('Cannot connect to the server. Check backend and network.');
  }

  let data = null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await res.json();
  } else {
    const text = await res.text();
    data = text ? { message: text } : {};
  }

  if (!res.ok) {
    const err = new Error(data.message || `Request failed (${res.status})`);
    err.status = res.status;
    throw err;
  }

  return data;
};

// ── Student Management ────────────────────────────────────────────────────────

/**
 * Register a new student or update existing student
 * @param {Object} student - Student data
 * @param {string} student.id - Student ID
 * @param {string} student.name - Student name
 * @param {string} student.class - Student class
 * @param {string[]} student.photos - Array of base64 encoded photos
 * @returns {Promise<Object>} Response with success status and message
 */
export const registerStudent = async (student) => {
  return api('/api/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(student),
  });
};

/**
 * Get all registered students
 * @returns {Promise<Object>} Response with students array
 */
export const getStudents = async () => {
  return api('/api/students');
};

/**
 * Delete a student by ID
 * @param {string} studentId - Student ID to delete
 * @returns {Promise<Object>} Response with success status and message
 */
export const deleteStudent = async (studentId) => {
  return api(`/api/students/${studentId}`, {
    method: 'DELETE',
  });
};

const getClientLocalClock = () => {
  const now = new Date();
  const pad = value => String(value).padStart(2, '0');

  return {
    client_date: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`,
    client_time: `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`,
  };
};

// ── Face Detection & Recognition ──────────────────────────────────────────────

/**
 * Detect faces in a frame (for real-time overlay, no attendance marking)
 * @param {string} frameBase64 - Base64 encoded image frame
 * @returns {Promise<Object>} Response with faces array containing detection results
 */
export const detectFaces = async (frameBase64) => {
  const clientClock = getClientLocalClock();
  return api('/api/detect', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame: frameBase64,
      ...clientClock,
    }),
  });
};

/**
 * Scan face and mark attendance
 * @param {string} frameBase64 - Base64 encoded image frame
 * @returns {Promise<Object>} Response with faces array containing recognition and attendance results
 */
export const scanAndMarkAttendance = async (frameBase64) => {
  const clientClock = getClientLocalClock();
  return api('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame: frameBase64,
      ...clientClock,
    }),
  });
};

// ── Attendance Records ────────────────────────────────────────────────────────

/**
 * Get attendance records with optional filters
 * @param {Object} filters - Filter options
 * @param {string} filters.date - Filter by date (YYYY-MM-DD format)
 * @param {string} filters.name - Filter by student name (partial match)
 * @param {string} filters.class - Filter by class
 * @returns {Promise<Object>} Response with records array
 */
export const getRecords = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.date) params.set('date', filters.date);
  if (filters.name) params.set('name', filters.name);
  if (filters.class) params.set('class', filters.class);
  
  const queryString = params.toString();
  const url = queryString ? `/api/records?${queryString}` : '/api/records';
  
  return api(url);
};

/**
 * Delete all attendance records
 * @returns {Promise<Object>} Response with deleted count
 */
export const clearRecords = async () => {
  try {
    return await api('/api/records', {
      method: 'DELETE',
    });
  } catch (e) {
    if (e?.status === 405) {
      return api('/api/records/clear', {
        method: 'POST',
      });
    }
    throw e;
  }
};

// ── Statistics ────────────────────────────────────────────────────────────────

/**
 * Get attendance statistics
 * @returns {Promise<Object>} Response with total_students, today_total, today_ontime, today_late, today
 */
export const getStats = async () => {
  const { client_date } = getClientLocalClock();
  return api(`/api/stats?date=${encodeURIComponent(client_date)}`);
};

// ── Student Images ────────────────────────────────────────────────────────────

/**
 * Get student image URL
 * @param {string} filename - Image filename (e.g., "ST001.jpg")
 * @returns {string} Full URL to the student image
 */
export const getStudentImageUrl = (filename) => {
  return `${API_BASE}/student_images/${filename}`;
};

// ── Export all functions as default object for convenience ─────────────────────
export default {
  registerStudent,
  getStudents,
  deleteStudent,
  detectFaces,
  scanAndMarkAttendance,
  getRecords,
  clearRecords,
  getStats,
  getStudentImageUrl,
};
