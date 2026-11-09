import ManagementPage from '../components/ManagementPage';

const fields = [
  { name: 'name', label: 'Name', type: 'text', required: true },
  { name: 'code', label: 'Code', type: 'text', required: true },
  { name: 'subject_type', label: 'Type', type: 'select', required: true, options: ['THEORY', 'LAB'] },
  { name: 'weekly_periods', label: 'Weekly periods', type: 'number', required: true, min: 1 },
  { name: 'academic_year_id', label: 'Academic year', type: 'select', required: true, optionsEndpoint: '/academic-years', coerceNumber: true },
  { name: 'faculty_id', label: 'Faculty', type: 'select', required: true, optionsEndpoint: '/faculty', coerceNumber: true },
];
const columns = [
  { key: 'name', label: 'Name' },
  { key: 'code', label: 'Code' },
  { key: 'subject_type', label: 'Type' },
  { key: 'weekly_periods', label: 'Weekly Periods' },
  { key: 'academic_year_id', label: 'Academic Year', render: (subject, options) => options.academic_year_id?.find((year) => year.id === subject.academic_year_id)?.name || subject.academic_year_id },
  { key: 'faculty_id', label: 'Faculty', render: (subject, options) => options.faculty_id?.find((member) => member.id === subject.faculty_id)?.name || subject.faculty_id },
];

export default function SubjectsPage() {
  return <ManagementPage title="Subjects" description="Manage subjects assigned to your department's academic years." endpoint="/subjects" columns={columns} fields={fields} />;
}
