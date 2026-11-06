import { RISK_LEVELS, type RouteSummary } from '../api/types'
import { formatMiles } from '../lib/format'
import { RISK_COLORS, RISK_LABELS } from '../lib/risk'
import styles from './Results.module.css'

const SUMMARY_FIELDS = ['low_mi', 'moderate_mi', 'high_mi', 'severe_mi', 'no_travel_mi'] as const

export function RiskBar({ summary }: { summary: RouteSummary }) {
  const total = SUMMARY_FIELDS.reduce((sum, field) => sum + summary[field], 0)
  const parts = RISK_LEVELS.map((level) => ({
    level,
    miles: summary[SUMMARY_FIELDS[level]],
  })).filter((part) => part.miles > 0)
  const description = parts
    .map((part) => `${RISK_LABELS[part.level]} ${formatMiles(part.miles)}`)
    .join(', ')
  return (
    <div className={styles.riskBar} role="img" aria-label={`Miles by risk: ${description}`}>
      {parts.map((part) => (
        <span
          key={part.level}
          title={`${RISK_LABELS[part.level]}: ${formatMiles(part.miles)}`}
          style={{
            flexGrow: total > 0 ? part.miles / total : 1,
            background: RISK_COLORS[part.level],
          }}
        />
      ))}
    </div>
  )
}
