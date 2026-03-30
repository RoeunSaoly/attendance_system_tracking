<template>
  <div class="page">
    <div class="page-header">
      <h2>Attendance Records</h2>
      <p class="subtitle">Search, review, and export class history.</p>
    </div>

    <div class="card filter-card">
      <div class="filter-group">
        <label>Date</label>
        <input type="date" v-model="filters.date" @input="applyFilters" />
      </div>

      <div class="filter-group">
        <label>Name</label>
        <input type="text" v-model="filters.name" @input="applyFilters" placeholder="Search student" />
      </div>

      <div class="filter-group">
        <label>Class</label>
        <input type="text" v-model="filters.class" @input="applyFilters" placeholder="e.g. 11A" />
      </div>

      <button @click="clearFilters" class="btn btn-gray">Clear</button>
      <button @click="exportCSV" class="btn btn-blue ml-auto">Export CSV</button>
    </div>

    <div class="card table-card">
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Class</th>
              <th>Date</th>
              <th>Time</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(record, idx) in store.records" :key="`${record.student_id}_${record.date}_${record.time}_${idx}`">
              <td>{{ record.student_id }}</td>
              <td>{{ record.name }}</td>
              <td>{{ record.class || '-' }}</td>
              <td>{{ record.date }}</td>
              <td>{{ record.time }}</td>
              <td>
                <span class="status-badge" :class="badgeClass(record.status)">
                  {{ record.status }}
                </span>
              </td>
            </tr>

            <tr v-if="store.records.length === 0">
              <td colspan="6" class="empty-row">No records found.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue';
import { useAttendanceStore } from '@/stores/attendance';
import { useToast } from '@/composables/useToast';
import { getRecords } from '@/services/api';

const store = useAttendanceStore();
const toast = useToast();

const filters = reactive({
  date: '',
  name: '',
  class: ''
});

const applyFilters = () => {
  store.fetchRecords(filters);
};

const clearFilters = () => {
  filters.date = '';
  filters.name = '';
  filters.class = '';
  store.fetchRecords({});
};

const badgeClass = (status) => {
  if (status === 'LATE') return 'late';
  if (status === 'EARLY') return 'early';
  return 'ontime';
};

const exportCSV = async () => {
  try {
    const data = await getRecords(filters);
    if (!data.records?.length) {
      toast.show('No data to export.');
      return;
    }

    const rows = [
      ['ID', 'Name', 'Class', 'Date', 'Time', 'Status'],
      ...data.records.map((record) => [
        record.student_id,
        record.name,
        record.class || '',
        record.date,
        record.time,
        record.status
      ])
    ];

    const csv = rows
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'attendance_records.csv';
    link.click();
    URL.revokeObjectURL(link.href);

    toast.show('CSV exported.');
  } catch (e) {
    toast.show(e.message || 'Failed to export CSV.', true);
  }
};

onMounted(() => {
  store.fetchRecords();
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

.card {
  background: rgba(17, 23, 40, 0.82);
  backdrop-filter: blur(10px);
  border-radius: 24px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.18);
}

.filter-card {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: flex-end;
  margin-bottom: 22px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #9fb2cf;
}

input {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  padding: 10px 16px;
  color: #f4f8ff;
  min-width: 180px;
  transition: 0.2s;
}

input:focus {
  outline: none;
  border-color: #2ec4b6;
  box-shadow: 0 0 0 2px rgba(46, 196, 182, 0.2);
}

input::placeholder {
  color: #90a4c0;
}

.table-card {
  overflow: hidden;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: rgba(255, 255, 255, 0.06);
}

th {
  text-align: left;
  padding: 14px 12px;
  font-size: 0.72rem;
  color: #f5f9ff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.16);
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

td {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  color: #f0f7ff;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-badge.ontime {
  background: rgba(46, 196, 182, 0.2);
  color: #2ec4b6;
}

.status-badge.early {
  background: rgba(91, 192, 235, 0.2);
  color: #5bc0eb;
}

.status-badge.late {
  background: rgba(255, 77, 109, 0.2);
  color: #ff7a93;
}

.empty-row {
  text-align: center;
  color: #b9cde8;
  padding: 32px !important;
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

.btn-blue {
  background: #00a6fb;
  color: #06233a;
}

.btn-gray {
  background: rgba(255, 255, 255, 0.12);
  color: #e8f3ff;
}

.btn:hover {
  transform: translateY(-2px);
  filter: brightness(1.05);
}

.ml-auto {
  margin-left: auto;
}

@media (max-width: 760px) {
  .filter-card {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-group,
  input {
    width: 100%;
  }

  .ml-auto {
    margin-left: 0;
  }
}
</style>
