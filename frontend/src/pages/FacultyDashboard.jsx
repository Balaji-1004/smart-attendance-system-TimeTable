import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';

export default function FacultyDashboard() {
  return (
    <>
      <PageHeader title="Faculty Dashboard" description="Attendance operations and timetable access." />
      <div className="dashboard-grid">
        <Card>
          <h3>Overview</h3>
          <p>This faculty dashboard is ready for the next Phase. The existing attendance and timetable pages remain available from the sidebar.</p>
        </Card>
      </div>
    </>
  );
}
