import Modal from './Modal';
import Button from './Button';

export default function ConfirmDialog({ open, title = 'Confirm', message, confirmText = 'Confirm', cancelText = 'Cancel', onConfirm, onCancel }) {
  return (
    <Modal open={open} title={title} onClose={onCancel}>
      <p>{message}</p>
      <div className="dialog-actions">
        <Button variant="secondary" onClick={onCancel}>{cancelText}</Button>
        <Button variant="danger" onClick={onConfirm}>{confirmText}</Button>
      </div>
    </Modal>
  );
}
