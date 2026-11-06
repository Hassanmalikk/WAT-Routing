const MINUTE_MS = 60_000
const ROUND_TO_MINUTES = 15
export const PAST_TOLERANCE_MS = 15 * MINUTE_MS
export const MAX_AHEAD_MS = 14 * 24 * 60 * MINUTE_MS

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

export function toLocalInputValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

export function defaultDeparture(now: Date): Date {
  const step = ROUND_TO_MINUTES * MINUTE_MS
  return new Date(Math.ceil(now.getTime() / step) * step)
}

export function departureError(value: string, now: Date): string | null {
  const departure = new Date(value)
  if (!value || Number.isNaN(departure.getTime())) return 'Enter a departure date and time.'
  if (departure.getTime() < now.getTime() - PAST_TOLERANCE_MS) {
    return 'Departure cannot be in the past.'
  }
  if (departure.getTime() > now.getTime() + MAX_AHEAD_MS) {
    return 'Departure must be within the next 14 days.'
  }
  return null
}
