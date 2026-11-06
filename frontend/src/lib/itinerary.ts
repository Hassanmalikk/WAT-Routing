import type { Checkpoint, Position, RiskLevel, Route, Stop } from '../api/types'
import { RISK_LABELS } from './risk'

export type ItineraryEvent =
  | { kind: 'depart' | 'arrive'; time: string; mile: number; position: Position }
  | { kind: 'drive'; time: string; mile: number; miles: number; duration_s: number }
  | {
      kind: 'weather'
      time: string
      mile: number
      level: RiskLevel
      reason: string
      checkpoint: number
    }
  | { kind: Stop['kind']; time: string; end: string; mile: number; position: Position }

export interface ItineraryDay {
  key: string
  date: string
  events: ItineraryEvent[]
}

function weatherReason(checkpoint: Checkpoint): string {
  const { conditions, risk } = checkpoint
  if (risk.wind === risk.level) {
    const wind = `Wind ${Math.round(conditions.wind_mph)} mph`
    return risk.load_adjusted ? `${wind}, raised for this load` : wind
  }
  if (risk.rain === risk.level) return `Rain ${conditions.rain_in_hr.toFixed(2)} in/hr`
  return `Snow ${conditions.snow_in_hr.toFixed(2)} in/hr`
}

export function buildItinerary(route: Route): ItineraryEvent[] {
  const origin = route.checkpoints[0]
  const destination = route.checkpoints.at(-1)
  if (!origin || !destination) return []

  const anchors = [
    { time: route.departure, end: route.departure, mile: 0, stop: null },
    ...route.stops.map((stop) => ({ time: stop.start, end: stop.end, mile: stop.mile, stop })),
    { time: route.arrival, end: route.arrival, mile: route.distance_mi, stop: null },
  ]
  const events: ItineraryEvent[] = [
    { kind: 'depart', time: route.departure, mile: 0, position: origin.position },
  ]
  for (let index = 1; index < anchors.length; index += 1) {
    const from = anchors[index - 1]
    const to = anchors[index]
    if (!from || !to) continue
    events.push({
      kind: 'drive',
      time: from.end,
      mile: from.mile,
      miles: to.mile - from.mile,
      duration_s: (Date.parse(to.time) - Date.parse(from.end)) / 1000,
    })
    const lastLeg = index === anchors.length - 1
    route.checkpoints.forEach((checkpoint, checkpointIndex) => {
      const inLeg = checkpoint.mile >= from.mile && (checkpoint.mile < to.mile || lastLeg)
      if (inLeg && checkpoint.risk.level > 0) {
        events.push({
          kind: 'weather',
          time: checkpoint.eta,
          mile: checkpoint.mile,
          level: checkpoint.risk.level,
          reason: `${RISK_LABELS[checkpoint.risk.level]} · ${weatherReason(checkpoint)}`,
          checkpoint: checkpointIndex,
        })
      }
    })
    if (to.stop) {
      events.push({
        kind: to.stop.kind,
        time: to.stop.start,
        end: to.stop.end,
        mile: to.stop.mile,
        position: to.stop.position,
      })
    }
  }
  events.push({
    kind: 'arrive',
    time: route.arrival,
    mile: route.distance_mi,
    position: destination.position,
  })
  return events
}

const dayKeyFormat = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})
const dayLabelFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'long',
  month: 'short',
  day: 'numeric',
})

export function groupByDay(events: ItineraryEvent[]): ItineraryDay[] {
  const days: ItineraryDay[] = []
  for (const event of events) {
    const moment = new Date(event.time)
    const key = dayKeyFormat.format(moment)
    const last = days.at(-1)
    if (last?.key === key) last.events.push(event)
    else days.push({ key, date: dayLabelFormat.format(moment), events: [event] })
  }
  return days
}
