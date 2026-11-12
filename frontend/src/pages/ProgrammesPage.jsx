import ManagementPage from '../components/ManagementPage';

const fields = [{ name: 'name', label: 'Name', type: 'text', required: true }];
const columns = [{ key: 'name', label: 'Name' }];

export default function ProgrammesPage() {
  return <ManagementPage title="Programmes" description="Manage department programmes." endpoint="/programmes" columns={columns} fields={fields} />;
}
