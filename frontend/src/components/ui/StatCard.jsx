export default function StatCard({ label, value, hint, icon, className = '' }) {
  return (
    <div className={`stat-card ${className}`.trim()}>
      <div className="stat-card__header">
        {icon ? <span className="stat-card__icon">{icon}</span> : null}
        <span className="stat-card__label">{label}</span>
      </div>
      <div className="stat-card__value">{value}</div>
      {hint ? <div className="stat-card__hint">{hint}</div> : null}
    </div>
  );
}
