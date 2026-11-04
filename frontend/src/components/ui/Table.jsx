export default function Table({ headers = [], rows = [], className = '' }) {
  return (
    <div className={`table-wrap ${className}`.trim()}>
      <table className="data-table">
        {headers.length > 0 ? (
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
        ) : null}
        <tbody>{rows}</tbody>
      </table>
    </div>
  );
}
