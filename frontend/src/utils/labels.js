export function yearLabel(year) {
  if (!year) return '';
  return year.programme_name ? `${year.programme_name} - ${year.name}` : year.name;
}
