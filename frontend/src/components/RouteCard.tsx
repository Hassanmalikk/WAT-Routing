import type { Route } from '../api/types'
import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { routeLetter, routeName } from '../lib/routes'
import surface from '../styles/surface.module.css'
import styles from './Results.module.css'
import { RiskBar } from './RiskBar'

interface RouteCardProps {
  route: Route
  index: number
  recommended: boolean
  selected: boolean
  onSelect: (index: number) => void
}

export function RouteCard({ route, index, recommended, selected, onSelect }: RouteCardProps) {
  const { summary } = route
  const stopTime = route.duration_s - route.driving_s
  return (
    <button
      type="button"
      className={`${surface.card} ${surface.rise} ${styles.routeCard}`}
      style={{ '--order': index + 1 }}
      aria-pressed={selected}
      onClick={() => onSelect(index)}
    >
      <span className={styles.routeHeader}>
        <span className={styles.avatar} aria-hidden="true">
          {routeLetter(index)}
        </span>
        <span className={styles.routeTitle}>
          <span className={styles.routeName}>{routeName(index)}</span>
          <span className={styles.routeMeta}>
            {formatMiles(route.distance_mi)} · {formatDuration(route.duration_s)}
            {stopTime > 0 && ` incl. ${formatDuration(stopTime)} stops`}
          </span>
        </span>
        {recommended && <span className={styles.badge}>Safest</span>}
      </span>
      <RiskBar summary={summary} />
      <span className={styles.stats}>
        <span>
          <small>Severe</small>
          {formatMiles(summary.severe_mi)}
        </span>
        <span>
          <small>High</small>
          {formatMiles(summary.high_mi)}
        </span>
        <span>
          <small>Avg risk</small>
          {summary.average_risk.toFixed(2)}
        </span>
        <span>
          <small>Arrive</small>
          {formatDateTime(route.arrival)}
        </span>
      </span>
      {summary.no_travel_mi > 0 && (
        <span className={styles.danger}>
          No-travel conditions on {formatMiles(summary.no_travel_mi)}
        </span>
      )}
    </button>
  )
}
