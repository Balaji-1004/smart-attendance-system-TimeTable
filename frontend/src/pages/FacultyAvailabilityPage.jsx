import { useEffect, useState } from 'react';
import api from '../services/api';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import ConfirmDialog from '../components/ui/ConfirmDialog';
import EmptyState from '../components/ui/EmptyState';
import ErrorMessage from '../components/ui/ErrorMessage';
import Modal from '../components/ui/Modal';
import PageHeader from '../components/ui/PageHeader';
import Spinner from '../components/ui/Spinner';
import Table from '../components/ui/Table';
import Toast from '../components/ui/Toast';

const days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY'];
const periods = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'];

function errorText(error, fallback) {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item) => item?.msg || JSON.stringify(item)).join('; ') : fallback;
}

export default function FacultyAvailabilityPage() {
  const [faculty, setFaculty] = useState([]);
  const [items, setItems] = useState([]);
  const [selectedFaculty, setSelectedFaculty] = useState('');
  const [form, setForm] = useState({ faculty_id: '', day: 'MONDAY', period: 'P1' });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [formError, setFormError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [facultyResponse, availabilityResponse] = await Promise.all([api.get('/faculty'), api.get('/faculty-availability')]);
      const members = facultyResponse.data || [];
      setFaculty(members);
      setItems(availabilityResponse.data || []);
      setSelectedFaculty((current) => current || String(members[0]?.id || ''));
    } catch (requestError) {
      setError(errorText(requestError, 'Failed to load faculty availability.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const openAdd = async () => {
    setFormError('');
    try {
      const response = await api.get('/faculty');
      const members = response.data || [];
      setFaculty(members);
      setForm({ faculty_id: String(members[0]?.id || ''), day: 'MONDAY', period: 'P1' });
    } catch (requestError) {
      setFormError(errorText(requestError, 'Failed to load faculty.'));
      setForm({ faculty_id: '', day: 'MONDAY', period: 'P1' });
    }
    setFormOpen(true);
  };

  const addAvailability = async (event) => {
    event.preventDefault();
    if (!form.faculty_id) return setFormError('Select a faculty member.');
    setSubmitting(true);
    setFormError('');
    try {
      await api.post('/faculty-availability', { ...form, faculty_id: Number(form.faculty_id) });
      setFormOpen(false);
      setToast({ message: 'Unavailable period added.', tone: 'success' });
      await loadData();
    } catch (requestError) {
      setFormError(errorText(requestError, 'Unable to save faculty availability.'));
    } finally {
      setSubmitting(false);
    }
  };

  const removeAvailability = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`/faculty-availability/${deleteTarget.id}`);
      setDeleteTarget(null);
      setToast({ message: 'Unavailable period deleted.', tone: 'success' });
      await loadData();
    } catch (requestError) {
      setToast({ message: errorText(requestError, 'Failed to delete availability.'), tone: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const currentFacultyId = selectedFaculty || String(faculty[0]?.id || '');
  const memberItems = items.filter((item) => String(item.faculty_id) === currentFacultyId);
  const rows = memberItems.map((item) => (
    <tr key={item.id}>
      <td>{item.day}</td><td>{item.period}</td>
      <td><Button variant="danger" onClick={() => setDeleteTarget(item)}>Delete</Button></td>
    </tr>
  ));

  return (
    <div className="management-page">
      <PageHeader title="Faculty Availability" description="Mark unavailable periods for faculty members." actions={<Button onClick={openAdd}>Add availability</Button>} />
      {loading ? <Spinner label="Loading faculty availability..." /> : null}
      {!loading && error ? <ErrorMessage message={error} onRetry={loadData} /> : null}
      {!loading && !error ? (
        <Card className="management-card">
          <div className="management-toolbar">
            <label className="form-field">Faculty member
              <select value={currentFacultyId} onChange={(event) => setSelectedFaculty(event.target.value)}>
                {faculty.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
              </select>
            </label>
          </div>
          {memberItems.length ? <Table headers={['Day', 'Period', 'Actions']} rows={rows} /> : <EmptyState title="No unavailable periods" description="No unavailable periods are recorded for this faculty member." />}
        </Card>
      ) : null}

      <Modal open={formOpen} title="Add unavailable period" onClose={() => setFormOpen(false)}>
        <form onSubmit={addAvailability} className="form-grid">
          <div className="form-field full">
            <label htmlFor="availability-faculty">Faculty member</label>
            <select id="availability-faculty" required value={form.faculty_id} onChange={(event) => setForm((current) => ({ ...current, faculty_id: event.target.value }))}>
              <option value="">Select faculty</option>
              {faculty.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="availability-day">Day</label>
            <select id="availability-day" value={form.day} onChange={(event) => setForm((current) => ({ ...current, day: event.target.value }))}>
              {days.map((day) => <option key={day} value={day}>{day}</option>)}
            </select>
          </div>
          <div className="form-field">
            <label htmlFor="availability-period">Period</label>
            <select id="availability-period" value={form.period} onChange={(event) => setForm((current) => ({ ...current, period: event.target.value }))}>
              {periods.map((period) => <option key={period} value={period}>{period}</option>)}
            </select>
          </div>
          {formError ? <p className="form-error full" role="alert">{formError}</p> : null}
          <div className="dialog-actions full">
            <Button variant="secondary" type="button" onClick={() => setFormOpen(false)}>Cancel</Button>
            <Button type="submit" loading={submitting}>Add period</Button>
          </div>
        </form>
      </Modal>
      <ConfirmDialog open={Boolean(deleteTarget)} title="Delete availability" message="Remove this unavailable period?" confirmText={deleting ? 'Deleting...' : 'Delete'} onConfirm={removeAvailability} onCancel={() => setDeleteTarget(null)} />
      {toast ? <Toast message={toast.message} tone={toast.tone} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
