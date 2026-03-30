import { defineStore } from 'pinia';
import { 
  getStudents, 
  getStats, 
  getRecords, 
  registerStudent as registerStudentApi,
  deleteStudent as deleteStudentApi,
  scanAndMarkAttendance,
  detectFaces as detectFacesApi
} from '@/services/api';
import { useToast } from '@/composables/useToast';

export const useAttendanceStore = defineStore('attendance', {
  state: () => ({
    students: [],
    stats: { total: 0, todayTotal: 0, ontime: 0, late: 0 },
    records: [],
    logs: [],
    lastScanErrorAt: 0,
  }),
  actions: {
    async fetchStudents() {
      try {
        const data = await getStudents();
        this.students = data.students;
      } catch (e) {
        const toast = useToast();
        toast.show(e.message, true);
      }
    },
    async fetchStats() {
      try {
        const data = await getStats();
        this.stats = {
          total: data.total_students,
          todayTotal: data.today_total,
          ontime: data.today_ontime,
          late: data.today_late,
        };
      } catch (e) {
        const toast = useToast();
        toast.show(e.message, true);
      }
    },
    async fetchRecords(filters = {}) {
      try {
        const data = await getRecords(filters);
        this.records = data.records;
      } catch (e) {
        const toast = useToast();
        toast.show(e.message, true);
      }
    },
    async registerStudent(student) {
      const toast = useToast();
      try {
        const res = await registerStudentApi(student);
        toast.show(res.message);
        if (res.success) await this.fetchStudents();
        return res;
      } catch (e) {
        toast.show(e.message, true);
        throw e;
      }
    },
    async deleteStudent(id, name) {
      const toast = useToast();
      if (!confirm(`Delete ${name}? This cannot be undone.`)) return;
      try {
        await deleteStudentApi(id);
        toast.show(`${name} deleted`);
        await this.fetchStudents();
      } catch (e) {
        toast.show(e.message, true);
      }
    },
    async markAttendance(frameBase64) {
      try {
        const res = await scanAndMarkAttendance(frameBase64);
        let processed = 0;
        if (res.faces?.length) {
          const nowText = new Date().toLocaleTimeString('en-GB', { hour12: false });
          res.faces.forEach(f => {
            if (!f.recognized) {
              this.addLog('Unknown', '', 'unknown', 'NO MATCH', nowText, f.score);
              processed += 1;
              return;
            }
            const status = f.status || (f.late ? 'LATE' : 'ON TIME');
            const type = f.already_marked ? 'already' : status === 'LATE' ? 'late' : 'ontime';
            this.addLog(f.name, f.class || '', type, status, f.time || nowText, f.score);
            processed += 1;
          });
          await this.fetchStats();
        }
        return {
          success: Boolean(res.success),
          message: res.message || '',
          processed,
        };
      } catch (e) {
        const now = Date.now();
        if (now - this.lastScanErrorAt > 6000) {
          this.lastScanErrorAt = now;
          const toast = useToast();
          toast.show(e.message || 'Attendance scan failed', true);
        }
        return {
          success: false,
          message: e.message || 'Attendance scan failed',
          processed: 0,
        };
      }
    },
    addDetectionLogs(faces = []) {
      if (!faces.length) return 0;

      const nowText = new Date().toLocaleTimeString('en-GB', { hour12: false });
      let added = 0;

      faces.forEach(face => {
        if (!face.recognized) {
          this.addLog('Unknown', '', 'unknown', 'NO MATCH', nowText, face.score);
          added += 1;
          return;
        }

        const type = face.already_marked ? 'already' : 'detected';
        const status = face.already_marked ? 'ALREADY MARKED' : 'DETECTED';
        this.addLog(face.name, face.class || '', type, status, nowText, face.score);
        added += 1;
      });

      return added;
    },
    async detectFaces(frameBase64) {
      try {
        const res = await detectFacesApi(frameBase64);
        return res.faces || [];
      } catch (e) {
        return [];
      }
    },
    addLog(name, cls, type, status, time, score = null) {
      const now = Date.now();
      const dayKey = new Date().toDateString();

      if (type === 'unknown') {
        const lastUnknown = this.logs.find(l => l.type === 'unknown');
        if (lastUnknown?.ts && now - lastUnknown.ts < 5000) return;
      }

      let key = `${name}_${dayKey}`;
      if (type === 'already') {
        key = `${name}_already_${dayKey}`;
        const lastAlready = this.logs.find(l => l.key === key);
        if (lastAlready?.ts && now - lastAlready.ts < 30000) return;
      } else if (type !== 'unknown' && this.logs.some(l => l.key === key)) {
        return;
      }

      this.logs.unshift({
        name,
        class: cls,
        type,
        status,
        time,
        score: typeof score === 'number' ? score : null,
        key: type === 'unknown' ? null : key,
        ts: now,
      });
      if (this.logs.length > 50) this.logs.pop();
    },
    clearLogs() {
      this.logs = [];
    },
  },
});
