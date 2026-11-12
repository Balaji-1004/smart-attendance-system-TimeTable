import ManagementPage from '../components/ManagementPage';
import { yearLabel } from '../utils/labels';

const fields = [
  { name: 'programme_id', label: 'Programme', type: 'select', required: true, optionsEndpoint: '/programmes', coerceNumber: true },
  { name: 'name', label: 'Name', type: 'text', required: true },
];
const columns = [
  { key: 'name', label: 'Name', render: (year) => yearLabel(year) },
  { key: 'programme_name', label: 'Programme' },
];

export default function AcademicYearsPage() {
  return <ManagementPage title="Academic Years" description="Manage academic years for your department." endpoint="/academic-years" columns={columns} fields={fields} />;
}
