export const WEEKDAYS = [
  { iso: 1, short: 'Mon' },
  { iso: 2, short: 'Tue' },
  { iso: 3, short: 'Wed' },
  { iso: 4, short: 'Thu' },
  { iso: 5, short: 'Fri' },
  { iso: 6, short: 'Sat' },
  { iso: 7, short: 'Sun' }
] as const

/**
 * ISO weekday for a date: 1 = Monday .. 7 = Sunday (D2).
 * JavaScript's getDay() is 0 = Sunday, so Sunday has to be moved to the end.
 */
export function isoWeekday(date: Date): number {
  const js = date.getDay()
  return js === 0 ? 7 : js
}

/**
 * "YYYY-MM-DD" in the *local* timezone.
 * toISOString() would convert to UTC first and can land on the wrong day, which
 * is exactly the bug specs.md section 4 warns about.
 */
export function toLocalIsoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

/** Parse "YYYY-MM-DD" as a local date, not a UTC instant. */
export function fromLocalIsoDate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function addDays(date: Date, days: number): Date {
  const next = new Date(date)
  next.setDate(next.getDate() + days)
  return next
}

/** "22:00:00" or "22:00" -> "22:00". Empty input stays empty. */
export function trimSeconds(time: string | null): string {
  if (!time) return ''
  return time.slice(0, 5)
}

/** Render a day set compactly: "Every day", "Weekdays", or "Mon, Wed, Fri". */
export function describeDays(days: number[]): string {
  const sorted = [...days].sort((a, b) => a - b)
  if (sorted.length === 7) return 'Every day'
  if (sorted.join() === '1,2,3,4,5') return 'Weekdays'
  if (sorted.join() === '6,7') return 'Weekends'
  return sorted.map((iso) => WEEKDAYS[iso - 1].short).join(', ')
}
