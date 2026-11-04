export default function Spinner({ size = 'medium', label = 'Loading...' }) {
  return (
    <div className="spinner-wrap" role="status" aria-live="polite">
      <span className={`spinner spinner-${size}`} />
      <span>{label}</span>
    </div>
  );
}
