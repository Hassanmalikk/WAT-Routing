const dateTimeFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short',
  hour: 'numeric',
  minute: '2-digit',
  timeZoneName: 'short',
})

const timeFormat = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })

const integerFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 })
const decimalFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 })

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso))
}

export function formatTime(iso: string): string {
  return timeFormat.format(new Date(iso))
}

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = totalMinutes % 60
  if (days > 0) return `${days} d ${hours} h`
  if (hours > 0) return `${hours} h ${String(minutes).padStart(2, '0')} min`
  return `${minutes} min`
}

export function formatMiles(miles: number): string {
  return `${(miles < 10 ? decimalFormat : integerFormat).format(miles)} mi`
}
