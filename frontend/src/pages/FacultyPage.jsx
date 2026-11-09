import ManagementPage from '../components/ManagementPage';

const fields = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'faculty_code', label: 'Faculty code', type: 'text', required: true },
  { name: 'email', label: 'Email', type: 'email', required: true },
  { name: 'username', label: 'Username', type: 'text', createOnly: true },
  { name: 'password', label: 'Password', type: 'password', createOnly: true },
];
const columns = [
  { key: 'name', label: 'Name' },
  { key: 'faculty_code', label: 'Faculty Code' },
  { key: 'email', label: 'Email' },
];

export default function FacultyPage() {
  return <ManagementPage title="Faculty" description="Manage department faculty and their login accounts." endpoint="/faculty" columns={columns} fields={fields} />;
}
