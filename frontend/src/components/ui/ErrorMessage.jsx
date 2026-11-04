export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-message" role="alert">
      <strong>Something went wrong</strong>
      <p>{message}</p>
      {onRetry ? <button type="button" className="button button-secondary" onClick={onRetry}>Retry</button> : null}
    </div>
  );
}
