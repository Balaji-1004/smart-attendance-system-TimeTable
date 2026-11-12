import ManagementPage from '../components/ManagementPage';
import { yearLabel } from '../utils/labels';

const fields = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'code', label: 'Code', type: 'text', required: true },
  { name: 'subject_type', label: 'Type', type: 'select', required: true, options: ['THEORY', 'LAB'] },
  { name: 'weekly_periods', label: 'Weekly periods', type: 'number', required: true, min: 1 },
  { name: 'academic_year_id', label: 'Academic year', type: 'select', required: true, optionsEndpoint: '/academic-years', optionLabel: yearLabel, coerceNumber: true },
  { name: 'faculty_id', label: 'Faculty', type: 'select', required: true, optionsEndpoint: '/faculty', coerceNumber: true },
];
const columns = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'subject_type', label: 'Type' },
];

export default function SubjectsPage() {
  return <ManagementPage title="Subjects" description="Manage subjects and assign any department faculty member to teach across programmes." endpoint="/subjects" columns={columns} fields={fields} />;
}
