import ManagementPage from '../components/ManagementPage';
import Badge from '../components/ui/Badge';

const fields = [
  { name: 'roll_number', label: 'Roll number', type: 'text', required: true },
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'email', label: 'Email', type: 'email', required: true },
  { name: 'academic_year_id', label: 'Academic year', type: 'select', required: true, optionsEndpoint: '/academic-years', coerceNumber: true },
  { name: 'username', label: 'Username', type: 'text', createOnly: true },
  { name: 'password', label: 'Password', type: 'password', createOnly: true },
];
const columns = [
  { key: 'roll_number', label: 'Roll Number' },
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'academic_year_id', label: 'Academic Year', render: (student, options) => options.academic_year_id?.find((year) => year.id === student.academic_year_id)?.name || student.academic_year_id },
  { key: 'face_registered', label: 'Face Registered', render: (student) => <Badge tone={student.face_registered ? 'success' : 'neutral'}>{student.face_registered ? 'Registered' : 'Unregistered'}</Badge> },
];

export default function StudentsPage() {
  return <ManagementPage title="Students" description="Manage students and their linked login accounts." endpoint="/students" columns={columns} fields={fields} />;
}
