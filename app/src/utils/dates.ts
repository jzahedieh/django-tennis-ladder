const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso.trim());
  if (match) {
    const year = match[1];
    const monthIdx = Number(match[2]) - 1;
    const day = Number(match[3]);
    const monthName = MONTHS[monthIdx];
    if (monthName && day >= 1 && day <= 31) {
      return `${day} ${monthName} ${year}`;
    }
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return `${parsed.getDate()} ${MONTHS[parsed.getMonth()]} ${parsed.getFullYear()}`;
}

export function formatDateRange(
  startIso: string | null | undefined,
  endIso: string | null | undefined
): string {
  const start = formatDate(startIso);
  const end = formatDate(endIso);
  if (start && end) return `${start} to ${end}`;
  return start || end;
}
