import type { FeatureCollection, Point } from 'geojson'
import type { ExpressionSpecification } from 'maplibre-gl'

import type { Heatmap, RiskLevel } from '../api/types'
import { RISK_COLORS, RISK_LABELS } from './risk'

export type HeatmapMetric = 'risk' | 'wind' | 'rain' | 'snow'

interface MetricSpec {
  label: string
  values: (heatmap: Heatmap) => number[][]
  ceiling: number
  bandFloors: readonly [number, number, number]
  legend: readonly string[]
}

export const HEATMAP_METRICS: Record<HeatmapMetric, MetricSpec> = {
  risk: {
    label: 'Risk',
    values: (heatmap) => heatmap.risk,
    ceiling: 4,
    bandFloors: [1, 2, 3],
    legend: ([0, 1, 2, 3, 4] as RiskLevel[]).map((level) => RISK_LABELS[level]),
  },
  wind: {
    label: 'Wind',
    values: (heatmap) => heatmap.wind_mph,
    ceiling: 55,
    bandFloors: [25, 35, 45],
    legend: ['< 25 mph', '25', '35', '45', '55+'],
  },
  rain: {
    label: 'Rain',
    values: (heatmap) => heatmap.rain_in_hr,
    ceiling: 1,
    bandFloors: [0.1, 0.25, 0.5],
    legend: ['< 0.10 in/hr', '0.10', '0.25', '0.50', '1.00+'],
  },
  snow: {
    label: 'Snow',
    values: (heatmap) => heatmap.snow_in_hr,
    ceiling: 3,
    bandFloors: [0.5, 1, 2],
    legend: ['< 0.5 in/hr', '0.5', '1.0', '2.0', '3.0+'],
  },
}

const LOW_TINT = 'rgba(31, 157, 99, 0.35)'
const BASE_WEIGHT = 0.15
const BAND_EDGE = 0.01

export const HEATMAP_LEGEND_COLORS = [
  LOW_TINT,
  RISK_COLORS[1],
  RISK_COLORS[2],
  RISK_COLORS[3],
  RISK_COLORS[4],
]

const KERNEL_SPACING_RATIO = 1.9
const WORLD_PX_PER_DEGREE_AT_Z0 = 512 / 360
const MAX_ZOOM = 22

function weight(value: number, ceiling: number): number {
  return BASE_WEIGHT + (1 - BASE_WEIGHT) * Math.min(Math.max(value / ceiling, 0), 1)
}

export function hourProperty(hour: number): string {
  return `h${hour}`
}

export function heatmapFeatures(
  heatmap: Heatmap,
  metric: HeatmapMetric,
): FeatureCollection<Point, Record<string, number>> {
  const { values, ceiling } = HEATMAP_METRICS[metric]
  const rows = values(heatmap)
  return {
    type: 'FeatureCollection',
    features: heatmap.cells.map((cell, index) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [cell.lon, cell.lat] },
      properties: Object.fromEntries(
        (rows[index] ?? []).map((value, hour) => [hourProperty(hour), weight(value, ceiling)]),
      ),
    })),
  }
}

export function heatmapRadius(heatmap: Heatmap): ExpressionSpecification {
  const meanLatitude =
    heatmap.cells.reduce((sum, cell) => sum + cell.lat, 0) / Math.max(heatmap.cells.length, 1)
  const verticalStretch = 1 / Math.sqrt(Math.cos((meanLatitude * Math.PI) / 180))
  const radiusAtZ0 =
    KERNEL_SPACING_RATIO * heatmap.cell_deg * WORLD_PX_PER_DEGREE_AT_Z0 * verticalStretch
  return [
    'interpolate',
    ['exponential', 2],
    ['zoom'],
    0,
    radiusAtZ0,
    MAX_ZOOM,
    radiusAtZ0 * 2 ** MAX_ZOOM,
  ]
}

export function heatmapColor(metric: HeatmapMetric): ExpressionSpecification {
  const { ceiling, bandFloors } = HEATMAP_METRICS[metric]
  const [moderate, high, severe] = bandFloors.map((floor) => weight(floor, ceiling)) as [
    number,
    number,
    number,
  ]
  return [
    'interpolate',
    ['linear'],
    ['heatmap-density'],
    0,
    'rgba(0,0,0,0)',
    BASE_WEIGHT,
    LOW_TINT,
    moderate - BAND_EDGE,
    LOW_TINT,
    moderate,
    RISK_COLORS[1],
    high,
    RISK_COLORS[2],
    severe,
    RISK_COLORS[3],
    1,
    RISK_COLORS[4],
  ]
}
