import ManagementPage from '../components/ManagementPage';

const fields = [
  { name: 'lab_code', label: 'Lab code', type: 'text', required: true },
  { name: 'name', label: 'Name', type: 'text', required: true },
];
const columns = [
  { key: 'lab_code', label: 'Lab Code' },
  { key: 'name', label: 'Name' },
];

export default function LabsPage() {
  return <ManagementPage title="Labs" description="Manage laboratory rooms and codes for this department." endpoint="/labs" columns={columns} fields={fields} />;
}
