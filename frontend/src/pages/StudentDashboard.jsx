import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';

export default function StudentDashboard() {
  return (
    <>
      <PageHeader title="Student Dashboard" description="Your attendance and class updates will appear here in a later phase." />
      <div className="dashboard-grid">
        <Card>
          <h3>Coming soon</h3>
          <p>This placeholder page is intentionally small and will be expanded in Phase 11D.</p>
        </Card>
      </div>
    </>
  );
}
