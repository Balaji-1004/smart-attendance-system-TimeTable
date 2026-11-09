import ManagementPage from '../components/ManagementPage';

const fields = [{ name: 'name', label: 'Name', type: 'text', required: true }];
const columns = [{ key: 'name', label: 'Name' }];

export default function AcademicYearsPage() {
  return <ManagementPage title="Academic Years" description="Manage academic years for your department." endpoint="/academic-years" columns={columns} fields={fields} />;
}
