import { describe, expect, it } from 'vitest'

import type { Heatmap, Recommendation, Route, RouteSummary } from '../api/types'
import { defaultDeparture, departureError } from './departure'
import { formatDuration, formatMiles } from './format'
import { heatmapColor, heatmapFeatures, heatmapRadius } from './heatmap'
import { parseLoad } from './load'
import { explainRecommendation, routeBounds, routeName } from './routes'

const SUMMARY: RouteSummary = {
  low_mi: 100,
  moderate_mi: 0,
  high_mi: 0,
  severe_mi: 0,
  no_travel_mi: 0,
  average_risk: 0,
}

function route(overrides: Partial<RouteSummary>, durationS = 3600): Route {
  return {
    distance_mi: 100,
    driving_s: durationS,
    duration_s: durationS,
    departure: '2026-11-07T08:00:00Z',
    arrival: '2026-11-07T09:00:00Z',
    summary: { ...SUMMARY, ...overrides },
    checkpoints: [],
    segments: [
      {
        level: 0,
        start_mile: 0,
        end_mile: 100,
        coordinates: [
          [-100, 40],
          [-99, 41],
        ],
      },
    ],
    stops: [],
  }
}

describe('formatting', () => {
  it('formats durations', () => {
    expect(formatDuration(35 * 60)).toBe('35 min')
    expect(formatDuration(5 * 3600 + 5 * 60)).toBe('5 h 05 min')
    expect(formatDuration(28 * 3600)).toBe('1 d 4 h')
  })

  it('formats miles with precision for short distances', () => {
    expect(formatMiles(3.25)).toBe('3.3 mi')
    expect(formatMiles(1234.4)).toBe('1,234 mi')
  })
})

describe('route helpers', () => {
  it('names routes alphabetically', () => {
    expect([0, 1, 2].map(routeName)).toEqual(['Route A', 'Route B', 'Route C'])
  })

  it('explains the deciding factor against the runner-up', () => {
    const routes = [route({ severe_mi: 42 }), route({ severe_mi: 0 })]
    const recommendation: Recommendation = {
      index: 1,
      deciding_factor: 'severe_miles',
      runner_up_index: 0,
    }
    expect(explainRecommendation(routes, recommendation)).toBe(
      'Fewest severe miles: 0 mi vs 42 mi on Route A.',
    )
  })

  it('explains travel-time wins', () => {
    const routes = [route({}, 3600), route({}, 7200)]
    expect(
      explainRecommendation(routes, {
        index: 0,
        deciding_factor: 'travel_time',
        runner_up_index: 1,
      }),
    ).toBe('Equal weather exposure, and 1 h 00 min faster than Route B.')
  })

  it('handles a single route', () => {
    expect(
      explainRecommendation([route({})], {
        index: 0,
        deciding_factor: 'only_route',
        runner_up_index: null,
      }),
    ).toBe('Only one distinct truck route was found for this trip.')
  })

  it('computes bounds across all routes', () => {
    expect(routeBounds([route({})])).toEqual([
      [-100, 40],
      [-99, 41],
    ])
    expect(routeBounds([])).toBeNull()
  })
})

describe('heatmap', () => {
  const heatmap: Heatmap = {
    cell_deg: 0.25,
    cells: [
      { lat: 40, lon: -100 },
      { lat: 41, lon: -99 },
    ],
    hours: ['2026-11-07T08:00:00Z', '2026-11-07T09:00:00Z'],
    risk: [
      [0, 2],
      [4, 1],
    ],
    wind_mph: [
      [10, 110],
      [55, 27.5],
    ],
    rain_in_hr: [
      [0, 0],
      [0, 0],
    ],
    snow_in_hr: [
      [0, 0],
      [0, 0],
    ],
  }

  it('maps values onto weights with a visible floor for calm cells', () => {
    const risk = heatmapFeatures(heatmap, 'risk')
    expect(risk.features[0]?.properties).toEqual({ h0: 0.15, h1: 0.575 })
    expect(risk.features[1]?.geometry.coordinates).toEqual([-99, 41])
    const wind = heatmapFeatures(heatmap, 'wind')
    expect(wind.features[0]?.properties.h1).toBe(1)
    expect(wind.features[1]?.properties.h1).toBe(0.575)
  })

  it('scales kernel radius with zoom', () => {
    const radius = heatmapRadius(heatmap)
    expect(radius[0]).toBe('interpolate')
    const [atZero, atMax] = [radius[4] as number, radius[6] as number]
    expect(atMax / atZero).toBe(2 ** 22)
  })

  it('places color stops at band floors', () => {
    const stops = heatmapColor('rain')
      .slice(3)
      .filter((stop) => typeof stop === 'number')
    expect(stops).toEqual(
      [0, 0.15, 0.225, 0.235, 0.3625, 0.575, 1].map((value) => expect.closeTo(value, 6)),
    )
  })
})

describe('form parsing', () => {
  const now = new Date('2026-11-07T08:07:00')

  it('rounds the default departure up to the next quarter hour', () => {
    expect(defaultDeparture(now)).toEqual(new Date('2026-11-07T08:15:00'))
  })

  it('validates the departure window', () => {
    expect(departureError('', now)).toBe('Enter a departure date and time.')
    expect(departureError('2026-11-07T07:30', now)).toBe('Departure cannot be in the past.')
    expect(departureError('2026-11-07T08:00', now)).toBeNull()
    expect(departureError('2026-11-30T08:00', now)).toBe(
      'Departure must be within the next 14 days.',
    )
  })

  it('parses load weights', () => {
    expect(parseLoad('42,000')).toBe(42_000)
    expect(parseLoad(' 80000 ')).toBe(80_000)
    expect(parseLoad('80001')).toBeNull()
    expect(parseLoad('0')).toBeNull()
    expect(parseLoad('12.5')).toBeNull()
    expect(parseLoad('abc')).toBeNull()
  })
})
