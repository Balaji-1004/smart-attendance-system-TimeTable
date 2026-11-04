import Card from '../components/ui/Card';

export default function NotFound() {
  return (
    <Card className="empty-state-card">
      <h1>404</h1>
      <h2>Page not found</h2>
      <p>The page you requested is not available in this app.</p>
    </Card>
  );
}
