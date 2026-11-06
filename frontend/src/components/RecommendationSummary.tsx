import { OctagonAlert, ShieldCheck, TriangleAlert } from 'lucide-react'

import type { TripPlan } from '../api/types'
import { formatMiles } from '../lib/format'
import { explainRecommendation, routeName } from '../lib/routes'
import surface from '../styles/surface.module.css'
import styles from './Results.module.css'

const TONE_ICONS = { safe: ShieldCheck, caution: TriangleAlert, danger: OctagonAlert }

export function RecommendationSummary({ plan }: { plan: TripPlan }) {
  const { routes, recommendation } = plan
  const best = routes[recommendation.index]
  if (!best) return null
  const { no_travel_mi: noTravel, severe_mi: severe } = best.summary
  const tone = noTravel > 0 ? 'danger' : severe > 0 ? 'caution' : 'safe'
  const Icon = TONE_ICONS[tone]
  return (
    <section
      className={`${surface.card} ${surface.rise} ${styles.hero}`}
      data-tone={tone}
      aria-live="polite"
    >
      <span className={styles.heroIcon} aria-hidden="true">
        <Icon />
      </span>
      <div className={styles.heroBody}>
        <span className={styles.eyebrow}>Recommendation</span>
        <h2 className={styles.heroTitle}>{routeName(recommendation.index)} is safest</h2>
        <p>{explainRecommendation(routes, recommendation)}</p>
        {tone === 'danger' && (
          <p className={styles.callout}>
            Every route crosses no-travel conditions ({formatMiles(noTravel)} on the best option).
            Consider delaying departure.
          </p>
        )}
        {tone === 'caution' && (
          <p className={styles.callout}>
            Expect severe conditions on {formatMiles(severe)} of this route.
          </p>
        )}
      </div>
    </section>
  )
}
