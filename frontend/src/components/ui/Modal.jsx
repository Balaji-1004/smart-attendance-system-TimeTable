export default function Modal({ open, title, onClose, children }) {
  if (!open) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal__header">
          <h3>{title}</h3>
          <button type="button" className="icon-button" onClick={onClose}>×</button>
        </div>
        <div className="modal__body">{children}</div>
      </div>
    </div>
  );
}
