import type { ExpressionSpecification } from 'maplibre-gl'

import type { RiskLevel } from '../api/types'

export const RISK_LABELS: Record<RiskLevel, string> = {
  0: 'Low',
  1: 'Moderate',
  2: 'High',
  3: 'Severe',
  4: 'No travel',
}

export const RISK_COLORS: Record<RiskLevel, string> = {
  0: '#1f9d63',
  1: '#d9a400',
  2: '#ef7d22',
  3: '#d6332a',
  4: '#7a1f5c',
}

export function riskColorExpression(property: string): ExpressionSpecification {
  return [
    'match',
    ['get', property],
    0,
    RISK_COLORS[0],
    1,
    RISK_COLORS[1],
    2,
    RISK_COLORS[2],
    3,
    RISK_COLORS[3],
    4,
    RISK_COLORS[4],
    RISK_COLORS[0],
  ]
}
