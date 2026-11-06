import { describe, expect, it } from 'vitest'

import type { Checkpoint, Route, RiskLevel } from '../api/types'
import { buildItinerary, groupByDay } from './itinerary'

const HOUR = 3_600_000
const DEPARTURE = Date.parse('2026-11-07T08:00:00Z')

function at(hours: number): string {
  return new Date(DEPARTURE + hours * HOUR).toISOString()
}

function checkpoint(mile: number, hours: number, level: RiskLevel = 0): Checkpoint {
  return {
    mile,
    position: { lat: 40, lon: -100 + mile / 100 },
    eta: at(hours),
    conditions: { wind_mph: level ? 40 : 5, gust_mph: 9, rain_in_hr: 0, snow_in_hr: 0 },
    risk: { level, wind: level, rain: 0, snow: 0, load_adjusted: level === 3 },
  }
}

const ROUTE: Route = {
  distance_mi: 650,
  driving_s: 10 * 3600,
  duration_s: 10.5 * 3600,
  departure: at(0),
  arrival: at(10.5),
  summary: {
    low_mi: 650,
    moderate_mi: 0,
    high_mi: 0,
    severe_mi: 0,
    no_travel_mi: 0,
    average_risk: 0,
  },
  checkpoints: [
    checkpoint(0, 0),
    checkpoint(300, 4.6, 2),
    checkpoint(600, 9.7, 3),
    checkpoint(650, 10.5),
  ],
  segments: [],
  stops: [
    { kind: 'break', mile: 520, position: { lat: 40, lon: -94.8 }, start: at(8), end: at(8.5) },
  ],
}

describe('itinerary', () => {
  it('orders departure, driving legs, weather, stops and arrival', () => {
    const events = buildItinerary(ROUTE)
    expect(events.map((event) => event.kind)).toEqual([
      'depart',
      'drive',
      'weather',
      'break',
      'drive',
      'weather',
      'arrive',
    ])
  })

  it('measures each driving leg between stops', () => {
    const legs = buildItinerary(ROUTE).filter((event) => event.kind === 'drive')
    expect(legs.map((leg) => [leg.mile, leg.miles, leg.duration_s])).toEqual([
      [0, 520, 8 * 3600],
      [520, 130, 2 * 3600],
    ])
  })

  it('explains what raised the weather risk', () => {
    const weather = buildItinerary(ROUTE).filter((event) => event.kind === 'weather')
    expect(weather.map((event) => event.reason)).toEqual([
      'High · Wind 40 mph',
      'Severe · Wind 40 mph, raised for this load',
    ])
    expect(weather.map((event) => event.checkpoint)).toEqual([1, 2])
  })

  it('groups events by calendar day', () => {
    const days = groupByDay(buildItinerary(ROUTE))
    expect(days.flatMap((day) => day.events)).toHaveLength(7)
    expect(new Set(days.map((day) => day.key)).size).toBe(days.length)
  })
})
