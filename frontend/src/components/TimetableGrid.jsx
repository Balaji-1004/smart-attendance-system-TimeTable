import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const DAYS = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY'];
const PERIODS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'];

function CellContent({ entry }) {
  const lines = entry.lab_name
    ? [entry.subject_name, entry.faculty_name, entry.lab_name]
    : [entry.subject_name, entry.faculty_name];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '11px', lineHeight: '1.4' }}>
      {lines.map((line, index) => <span key={`${entry.id}-${index}`}>{line}</span>)}
    </div>
  );
}

function EditForm({ entry, labs, onSave, onDelete, onCancel }) {
  const [day, setDay] = useState(entry.day);
  const [period, setPeriod] = useState(entry.period);
  const [labId, setLabId] = useState(entry.lab_id == null ? '' : String(entry.lab_id));
  const [validationErrors, setValidationErrors] = useState([]);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    setValidationErrors([]);
    try {
      await onSave(entry.id, {
        day,
        period,
        lab_id: labId === '' ? null : Number(labId),
      });
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setValidationErrors(Array.isArray(detail) ? detail : [detail || 'Failed to save timetable entry.']);
    } finally {
      setSaving(false);
    }
  };

  const remove = async () => {
    if (!window.confirm('Delete this timetable entry?')) return;
    setSaving(true);
    try {
      await onDelete(entry.id);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setValidationErrors(Array.isArray(detail) ? detail : [detail || 'Failed to delete timetable entry.']);
      setSaving(false);
    }
  };

  return (
    <div onClick={(event) => event.stopPropagation()} style={{ display: 'flex', flexDirection: 'column', gap: '5px', fontSize: '11px' }}>
      <select value={day} onChange={(event) => setDay(event.target.value)} aria-label="Edit day">
        {DAYS.map((option) => <option key={option}>{option}</option>)}
      </select>
      <select value={period} onChange={(event) => setPeriod(event.target.value)} aria-label="Edit period">
        {PERIODS.map((option) => <option key={option}>{option}</option>)}
      </select>
      <select value={labId} onChange={(event) => setLabId(event.target.value)} aria-label="Edit lab">
        <option value="">None</option>
        {labs.map((lab) => <option key={lab.id} value={lab.id}>{lab.name}</option>)}
      </select>
      {validationErrors.length > 0 && (
        <ul style={{ color: '#b91c1c', paddingLeft: '16px', margin: '2px 0' }}>
          {validationErrors.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}
        </ul>
      )}
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
        <button type="button" disabled={saving} onClick={save}>Save</button>
        <button type="button" disabled={saving} onClick={remove}>Delete</button>
        <button type="button" disabled={saving} onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

export default function TimetableGrid({ entries = [], onRefresh }) {
  const { role, faculty_id } = useAuth();
  const [editingEntryId, setEditingEntryId] = useState(null);
  const [labs, setLabs] = useState([]);
  const [labError, setLabError] = useState('');

  useEffect(() => {
    const loadLabs = async () => {
      try {
        const response = await api.get('/labs');
        setLabs(response.data || []);
      } catch (error) {
        setLabError(error?.response?.data?.detail || 'Failed to load labs for editing.');
      }
    };
    loadLabs();
  }, []);

  const saveEntry = async (entryId, payload) => {
    await api.put(`/timetable/${entryId}`, payload);
    setEditingEntryId(null);
    if (onRefresh) await onRefresh();
  };

  const deleteEntry = async (entryId) => {
    await api.delete(`/timetable/${entryId}`);
    setEditingEntryId(null);
    if (onRefresh) await onRefresh();
  };

  const cellLookup = new Map();
  entries.forEach((entry) => {
    const key = `${entry.day}-${entry.period}`;
    if (!cellLookup.has(key)) cellLookup.set(key, entry);
  });

  return (
    <div style={{ overflowX: 'auto' }}>
      {labError ? <p style={{ color: '#b91c1c' }}>{labError}</p> : null}
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: '760px', border: '1px solid #d1d5db' }}>
        <thead>
          <tr>
            <th style={{ border: '1px solid #d1d5db', background: '#f3f4f6', padding: '8px' }}>Time</th>
            {PERIODS.map((period) => <th key={period} style={{ border: '1px solid #d1d5db', background: '#f3f4f6', padding: '8px', minWidth: '110px' }}>{period}</th>)}
          </tr>
        </thead>
        <tbody>
          {DAYS.map((day) => (
            <tr key={day}>
              <th style={{ border: '1px solid #d1d5db', background: '#f3f4f6', padding: '8px', textAlign: 'left' }}>{day}</th>
              {PERIODS.map((period) => {
                const entry = cellLookup.get(`${day}-${period}`) || null;
                const canEdit = entry && (role === 'HOD' || (role === 'FACULTY' && entry.faculty_id === faculty_id));
                const editing = entry && editingEntryId === entry.id;
                return (
                  <td
                    key={`${day}-${period}`}
                    onClick={canEdit ? () => setEditingEntryId(entry.id) : undefined}
                    style={{ border: '1px solid #d1d5db', padding: '8px', verticalAlign: 'top', minHeight: '72px', background: entry ? '#f9fafb' : '#fff', cursor: canEdit ? 'pointer' : 'default' }}
                  >
                    {editing ? <EditForm entry={entry} labs={labs} onSave={saveEntry} onDelete={deleteEntry} onCancel={() => setEditingEntryId(null)} /> : entry ? <CellContent entry={entry} /> : null}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
