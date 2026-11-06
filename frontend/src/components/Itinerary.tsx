import { BedDouble, CloudAlert, Coffee, Flag, type LucideIcon, MapPin, Truck } from 'lucide-react'
import { useMemo } from 'react'

import type { PlannedTrip, Position, Route } from '../api/types'
import { formatDuration, formatMiles, formatTime } from '../lib/format'
import { buildItinerary, groupByDay, type ItineraryEvent } from '../lib/itinerary'
import { RISK_COLORS } from '../lib/risk'
import styles from './Summary.module.css'

const ICONS: Record<ItineraryEvent['kind'], LucideIcon> = {
  depart: MapPin,
  drive: Truck,
  weather: CloudAlert,
  break: Coffee,
  rest: BedDouble,
  arrive: Flag,
}

interface ItineraryProps {
  trip: PlannedTrip
  route: Route
  onFocusPosition: (position: Position) => void
  onFocusCheckpoint: (index: number) => void
}

function describe(event: ItineraryEvent, trip: PlannedTrip): { title: string; detail: string } {
  switch (event.kind) {
    case 'depart':
      return { title: `Depart ${trip.origin.label}`, detail: 'Mile 0' }
    case 'arrive':
      return { title: `Arrive ${trip.destination.label}`, detail: `Mile ${Math.round(event.mile)}` }
    case 'drive':
      return {
        title: `Drive ${formatMiles(event.miles)}`,
        detail: formatDuration(event.duration_s),
      }
    case 'weather':
      return { title: event.reason, detail: `Mile ${Math.round(event.mile)}` }
    case 'break':
    case 'rest':
      return {
        title: event.kind === 'rest' ? '10 h rest' : '30 min break',
        detail: `Mile ${Math.round(event.mile)} · until ${formatTime(event.end)}`,
      }
  }
}

export function Itinerary({ trip, route, onFocusPosition, onFocusCheckpoint }: ItineraryProps) {
  const days = useMemo(() => groupByDay(buildItinerary(route)), [route])

  function focus(event: ItineraryEvent) {
    if (event.kind === 'weather') onFocusCheckpoint(event.checkpoint)
    else if (event.kind !== 'drive') onFocusPosition(event.position)
  }

  return (
    <div className={styles.itinerary}>
      {days.map((day) => (
        <section key={day.key}>
          <h3 className={styles.day}>{day.date}</h3>
          <ol>
            {day.events.map((event) => {
              const Icon = ICONS[event.kind]
              const { title, detail } = describe(event, trip)
              const content = (
                <>
                  <span className={styles.eventIcon} aria-hidden="true">
                    <Icon />
                  </span>
                  <span className={styles.eventText}>
                    <strong>{title}</strong>
                    <span>{detail}</span>
                  </span>
                  <time dateTime={event.time}>{formatTime(event.time)}</time>
                </>
              )
              return (
                <li
                  key={`${event.kind}-${event.time}-${event.mile}`}
                  data-kind={event.kind}
                  style={
                    event.kind === 'weather' ? { '--risk': RISK_COLORS[event.level] } : undefined
                  }
                >
                  {event.kind === 'drive' ? (
                    <div className={styles.event}>{content}</div>
                  ) : (
                    <button type="button" className={styles.event} onClick={() => focus(event)}>
                      {content}
                    </button>
                  )}
                </li>
              )
            })}
          </ol>
        </section>
      ))}
    </div>
  )
}
