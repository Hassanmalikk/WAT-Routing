import type { Recommendation, Route } from '../api/types'
import { formatDuration, formatMiles } from './format'

export function routeLetter(index: number): string {
  return String.fromCharCode(65 + index)
}

export function routeName(index: number): string {
  return `Route ${routeLetter(index)}`
}

function compareMiles(label: string, best: number, other: number, otherName: string): string {
  return `Fewest ${label} miles: ${formatMiles(best)} vs ${formatMiles(other)} on ${otherName}.`
}

export function explainRecommendation(routes: Route[], recommendation: Recommendation): string {
  const best = routes[recommendation.index]
  const runnerUpIndex = recommendation.runner_up_index
  const other = runnerUpIndex === null ? undefined : routes[runnerUpIndex]
  if (!best || !other || runnerUpIndex === null) {
    return 'Only one distinct truck route was found for this trip.'
  }
  const otherName = routeName(runnerUpIndex)
  switch (recommendation.deciding_factor) {
    case 'no_travel_miles':
      return compareMiles(
        'no-travel',
        best.summary.no_travel_mi,
        other.summary.no_travel_mi,
        otherName,
      )
    case 'severe_miles':
      return compareMiles('severe', best.summary.severe_mi, other.summary.severe_mi, otherName)
    case 'high_miles':
      return compareMiles('high-risk', best.summary.high_mi, other.summary.high_mi, otherName)
    case 'average_risk':
      return `Lowest average risk: ${best.summary.average_risk.toFixed(2)} vs ${other.summary.average_risk.toFixed(2)} on ${otherName}.`
    case 'travel_time':
      return `Equal weather exposure, and ${formatDuration(other.duration_s - best.duration_s)} faster than ${otherName}.`
    case 'tie':
    case 'only_route':
      return `Equivalent to ${otherName} on weather risk and travel time.`
  }
}

export function routeBounds(routes: Route[]): [[number, number], [number, number]] | null {
  let minLon = Infinity
  let minLat = Infinity
  let maxLon = -Infinity
  let maxLat = -Infinity
  for (const route of routes) {
    for (const segment of route.segments) {
      for (const [lon, lat] of segment.coordinates) {
        minLon = Math.min(minLon, lon)
        minLat = Math.min(minLat, lat)
        maxLon = Math.max(maxLon, lon)
        maxLat = Math.max(maxLat, lat)
      }
    }
  }
  return Number.isFinite(minLon)
    ? [
        [minLon, minLat],
        [maxLon, maxLat],
      ]
    : null
}
