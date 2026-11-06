import { CloudRain, Snowflake, Wind } from 'lucide-react'
import { useEffect, useRef } from 'react'

import type { Route } from '../api/types'
import { formatDateTime } from '../lib/format'
import { RISK_COLORS, RISK_LABELS } from '../lib/risk'
import surface from '../styles/surface.module.css'
import styles from './Results.module.css'

const SHOWN_PRECIPITATION_IN_HR = 0.005

interface CheckpointListProps {
  route: Route
  activeIndex: number | null
  onFocus: (index: number) => void
}

export function CheckpointList({ route, activeIndex, onFocus }: CheckpointListProps) {
  const listRef = useRef<HTMLOListElement>(null)

  useEffect(() => {
    if (activeIndex !== null)
      listRef.current?.children[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  return (
    <ol ref={listRef} className={styles.timeline}>
      {route.checkpoints.map((checkpoint, index) => {
        const { conditions, risk } = checkpoint
        const mile = Math.round(checkpoint.mile)
        return (
          <li
            key={checkpoint.mile}
            className={surface.rise}
            style={{ '--order': index, '--risk': RISK_COLORS[risk.level] }}
          >
            <button
              type="button"
              className={styles.checkpoint}
              aria-current={index === activeIndex || undefined}
              aria-label={`Mile ${mile}, ${RISK_LABELS[risk.level]} risk, ETA ${formatDateTime(checkpoint.eta)}. Show on map.`}
              onClick={() => onFocus(index)}
            >
              <span className={styles.node} aria-hidden="true" />
              <span className={styles.checkpointMain}>
                <span className={styles.checkpointTitle}>Mile {mile}</span>
                <span className={styles.checkpointEta}>{formatDateTime(checkpoint.eta)}</span>
              </span>
              <span className={styles.readings} aria-hidden="true">
                <span>
                  <Wind />
                  {Math.round(conditions.wind_mph)} mph
                </span>
                {conditions.rain_in_hr >= SHOWN_PRECIPITATION_IN_HR && (
                  <span>
                    <CloudRain />
                    {conditions.rain_in_hr.toFixed(2)} in/hr
                  </span>
                )}
                {conditions.snow_in_hr >= SHOWN_PRECIPITATION_IN_HR && (
                  <span>
                    <Snowflake />
                    {conditions.snow_in_hr.toFixed(2)} in/hr
                  </span>
                )}
              </span>
              <span className={styles.level} aria-hidden="true">
                {RISK_LABELS[risk.level]}
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )
}
