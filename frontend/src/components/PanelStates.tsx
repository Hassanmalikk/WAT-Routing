import { CloudSun, RotateCw, ShieldCheck, TriangleAlert, Truck } from 'lucide-react'

import surface from '../styles/surface.module.css'
import styles from './PanelStates.module.css'

const STEPS = [
  {
    icon: Truck,
    title: 'Truck routes',
    text: 'Up to three truck-legal routes, sized for your gross weight.',
  },
  {
    icon: CloudSun,
    title: 'Forecast at your ETA',
    text: 'Weather is read at each checkpoint for the hour you reach it.',
  },
  {
    icon: ShieldCheck,
    title: 'Safest pick',
    text: 'Ranked by severe miles, then high-risk miles, average risk and time.',
  },
]

export function Welcome() {
  return (
    <ol className={styles.steps}>
      {STEPS.map(({ icon: Icon, title, text }, index) => (
        <li key={title} className={surface.rise} style={{ '--order': index + 1 }}>
          <span className={styles.stepIcon} aria-hidden="true">
            <Icon />
          </span>
          <span>
            <strong>{title}</strong>
            <span>{text}</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

export function PlanSkeleton() {
  return (
    <div className={styles.skeleton}>
      <div className={styles.progress} role="status">
        <span>Finding truck routes and reading forecasts along each one…</span>
        <span className={styles.track} aria-hidden="true" />
      </div>
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className={`${surface.card} ${surface.rise} ${styles.ghost}`}
          style={{ '--order': index }}
          aria-hidden="true"
        >
          <span className={styles.ghostHeader}>
            <i className={styles.ghostAvatar} />
            <i className={styles.ghostLine} />
          </span>
          <i className={styles.ghostBar} />
          <i className={styles.ghostLine} />
        </div>
      ))}
    </div>
  )
}

export function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className={`${surface.card} ${surface.rise} ${styles.error}`} role="alert">
      <span className={styles.errorIcon} aria-hidden="true">
        <TriangleAlert />
      </span>
      <div className={styles.errorBody}>
        <strong>Couldn’t plan this trip</strong>
        <p>{message}</p>
        <button type="button" className={styles.retry} onClick={onRetry}>
          <RotateCw aria-hidden="true" />
          Try again
        </button>
      </div>
    </div>
  )
}
