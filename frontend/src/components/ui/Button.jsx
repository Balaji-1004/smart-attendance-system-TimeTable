const variants = {
  primary: 'button button-primary',
  secondary: 'button button-secondary',
  danger: 'button button-danger',
};

export default function Button({ children, variant = 'primary', type = 'button', loading = false, className = '', disabled = false, ...props }) {
  return (
    <button
      type={type}
      className={`${variants[variant] || variants.primary} ${className}`.trim()}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? 'Loading...' : children}
    </button>
  );
}
