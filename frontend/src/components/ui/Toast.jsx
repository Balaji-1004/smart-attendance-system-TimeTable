export default function Toast({ message, tone = 'success', onClose }) {
  return (
    <div className={`toast toast-${tone}`} role="status">
      <span>{message}</span>
      {onClose ? <button type="button" className="icon-button" onClick={onClose}>×</button> : null}
    </div>
  );
}
