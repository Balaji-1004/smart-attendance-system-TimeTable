import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import Button from './ui/Button';
import Card from './ui/Card';
import ConfirmDialog from './ui/ConfirmDialog';
import EmptyState from './ui/EmptyState';
import ErrorMessage from './ui/ErrorMessage';
import Modal from './ui/Modal';
import PageHeader from './ui/PageHeader';
import Spinner from './ui/Spinner';
import Table from './ui/Table';
import Toast from './ui/Toast';

function responseDetail(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join('; ');
  }
  return fallback;
}

function optionParts(option, field) {
  if (typeof option !== 'object') return { value: option, label: option };
  const valueKey = field.optionValue || 'id';
  const labelKey = field.optionLabel || 'name';
  return {
    value: option[valueKey] ?? option.value,
    label: option[labelKey] ?? option.label ?? option[valueKey],
  };
}

export default function ManagementPage({
  title,
  description,
  endpoint,
  columns = [],
  fields = [],
  idKey = 'id',
  canCreate = true,
  canEdit = true,
  canDelete = true,
  transformPayload,
  onLoaded,
}) {
  const [items, setItems] = useState([]);
  const [options, setOptions] = useState({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [values, setValues] = useState({});
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toast, setToast] = useState(null);

  const loadOptions = useCallback(async () => {
    const optionFields = fields.filter((field) => field.optionsEndpoint);
    const endpoints = [...new Set(optionFields.map((field) => field.optionsEndpoint))];
    const responses = await Promise.all(endpoints.map((path) => api.get(path)));
    const fetched = Object.fromEntries(endpoints.map((path, index) => [path, responses[index].data || []]));
    setOptions(Object.fromEntries(optionFields.map((field) => [field.name, fetched[field.optionsEndpoint]])));
  }, [fields]);

  const loadItems = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const [response] = await Promise.all([api.get(endpoint), loadOptions()]);
      const data = Array.isArray(response.data) ? response.data : response.data?.items || [];
      setItems(data);
      await onLoaded?.(data);
    } catch (error) {
      setLoadError(responseDetail(error, `Failed to load ${title.toLowerCase()}.`));
    } finally {
      setLoading(false);
    }
  }, [endpoint, loadOptions, onLoaded, title]);

  useEffect(() => {
    loadItems();
  }, [loadItems]);

  const openForm = async (item = null) => {
    setEditingItem(item);
    setFormError('');
    setValues(item ? Object.fromEntries(fields.map((field) => [
      field.name,
      item[field.name] == null ? '' : String(item[field.name]),
    ])) : Object.fromEntries(fields.map((field) => [field.name, field.defaultValue ?? ''])));
    try {
      await loadOptions();
      setFormOpen(true);
    } catch (error) {
      setFormError(responseDetail(error, 'Failed to load form options.'));
      setFormOpen(true);
    }
  };

  const submitForm = async (event) => {
    event.preventDefault();
    const activeFields = fields.filter((field) => !(editingItem && field.createOnly));
    const missing = activeFields.find((field) => field.required && !String(values[field.name] ?? '').trim());
    if (missing) {
      setFormError(`${missing.label} is required.`);
      return;
    }
    if (['username', 'password'].every((name) => activeFields.some((field) => field.name === name))) {
      const username = String(values.username || '').trim();
      const password = String(values.password || '');
      if (Boolean(username) !== Boolean(password)) {
        setFormError('Both username and password must be provided together.');
        return;
      }
    }

    const payload = {};
    for (const field of activeFields) {
      const value = values[field.name];
      if (value === '' || value == null) continue;
      payload[field.name] = field.type === 'number' || field.coerceNumber ? Number(value) : typeof value === 'string' && field.type !== 'password' ? value.trim() : value;
    }

    setSubmitting(true);
    setFormError('');
    try {
      const body = transformPayload ? transformPayload(payload, editingItem ? 'edit' : 'create') : payload;
      if (editingItem) await api.put(`${endpoint}/${editingItem[idKey]}`, body);
      else await api.post(endpoint, body);
      setFormOpen(false);
      setToast({ message: `${title} ${editingItem ? 'updated' : 'created'} successfully.`, tone: 'success' });
      await loadItems();
    } catch (error) {
      setFormError(responseDetail(error, `Unable to save ${title.toLowerCase()}.`));
    } finally {
      setSubmitting(false);
    }
  };

  const deleteItem = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await api.delete(`${endpoint}/${deleteTarget[idKey]}`);
      setToast({ message: `${title} deleted successfully.`, tone: 'success' });
      setDeleteTarget(null);
      await loadItems();
    } catch (error) {
      setToast({ message: responseDetail(error, `Failed to delete ${title.toLowerCase()}.`), tone: 'error' });
    } finally {
      setDeleting(false);
    }
  };

  const showActions = canEdit || canDelete;
  const rows = items.map((item) => (
    <tr key={item[idKey]}>
      {columns.map((column) => (
        <td key={column.key}>{column.render ? column.render(item, options) : item[column.key]}</td>
      ))}
      {showActions ? (
        <td><div className="table-actions">
          {canEdit ? <Button variant="secondary" onClick={() => openForm(item)}>Edit</Button> : null}
          {canDelete ? <Button variant="danger" onClick={() => setDeleteTarget(item)}>Delete</Button> : null}
        </div></td>
      ) : null}
    </tr>
  ));

  return (
    <div className="management-page">
      <PageHeader title={title} description={description} actions={canCreate ? <Button onClick={() => openForm()}>{`Add ${title.replace(/s$/, '').toLowerCase()}`}</Button> : null} />
      {loading ? <Spinner label={`Loading ${title.toLowerCase()}...`} /> : null}
      {!loading && loadError ? <ErrorMessage message={loadError} onRetry={loadItems} /> : null}
      {!loading && !loadError ? (
        <Card className="management-card">
          <div className="management-toolbar">
            <strong>{title}</strong>
            {canCreate ? <Button onClick={() => openForm()}>{`Add ${title.replace(/s$/, '').toLowerCase()}`}</Button> : null}
          </div>
          {items.length ? (
            <Table headers={[...columns.map((column) => column.label), ...(showActions ? ['Actions'] : [])]} rows={rows} />
          ) : (
            <EmptyState title={`No ${title.toLowerCase()}`} description={`Add the first ${title.replace(/s$/, '').toLowerCase()}.`} />
          )}
        </Card>
      ) : null}

      <Modal open={formOpen} title={`${editingItem ? 'Edit' : 'Add'} ${title.replace(/s$/, '').toLowerCase()}`} onClose={() => setFormOpen(false)}>
        <form onSubmit={submitForm} className="form-grid">
          {fields.filter((field) => !(editingItem && field.createOnly)).map((field) => {
            const fieldOptions = field.options || options[field.name] || [];
            return (
              <div className={`form-field ${field.full ? 'full' : ''}`} key={field.name}>
                <label htmlFor={`management-${field.name}`}>{field.label}</label>
                {field.type === 'select' ? (
                  <select id={`management-${field.name}`} value={values[field.name] ?? ''} required={field.required} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))}>
                    <option value="">Select {field.label.toLowerCase()}</option>
                    {fieldOptions.map((option) => {
                      const part = optionParts(option, field);
                      return <option key={part.value} value={part.value}>{part.label}</option>;
                    })}
                  </select>
                ) : (
                  <input id={`management-${field.name}`} type={field.type || 'text'} value={values[field.name] ?? ''} required={field.required} min={field.min} onChange={(event) => setValues((current) => ({ ...current, [field.name]: event.target.value }))} />
                )}
              </div>
            );
          })}
          {formError ? <p className="form-error full" role="alert">{formError}</p> : null}
          <div className="dialog-actions full">
            <Button variant="secondary" type="button" onClick={() => setFormOpen(false)}>Cancel</Button>
            <Button type="submit" loading={submitting}>{editingItem ? 'Save changes' : 'Create'}</Button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title={`Delete ${title.replace(/s$/, '').toLowerCase()}`}
        message={`Delete “${deleteTarget?.name || deleteTarget?.[idKey]}”? This cannot be undone.`}
        confirmText={deleting ? 'Deleting...' : 'Delete'}
        onConfirm={deleteItem}
        onCancel={() => setDeleteTarget(null)}
      />
      {toast ? <Toast message={toast.message} tone={toast.tone} onClose={() => setToast(null)} /> : null}
    </div>
  );
}
