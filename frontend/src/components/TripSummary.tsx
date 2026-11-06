import { ArrowRight, ImageDown, Pencil, Printer, ShieldAlert, ShieldCheck } from 'lucide-react'

import type { PlannedTrip, TripPlan } from '../api/types'
import type { ExportKind } from '../hooks/useTripExport'
import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { routeName } from '../lib/routes'
import surface from '../styles/surface.module.css'
import styles from './Summary.module.css'

interface TripSummaryProps {
  trip: PlannedTrip
  plan: TripPlan
  selectedIndex: number
  exporting: ExportKind | null
  exportError: string | null
  editing: boolean
  onEdit: () => void
  onPrint: () => void
  onExportPng: () => void
  onShowChecks: () => void
}

export function TripSummary({
  trip,
  plan,
  selectedIndex,
  exporting,
  exportError,
  editing,
  onEdit,
  onPrint,
  onExportPng,
  onShowChecks,
}: TripSummaryProps) {
  const route = plan.routes[selectedIndex]
  if (!route) return null
  const { request } = trip
  const passed = plan.verification.checks.filter((check) => check.passed).length
  const total = plan.verification.checks.length
  const VerdictIcon = plan.verification.passed ? ShieldCheck : ShieldAlert
  const stopTime = route.duration_s - route.driving_s
  const stats = [
    { label: 'Distance', value: formatMiles(route.distance_mi) },
    {
      label: stopTime > 0 ? 'Total incl. stops' : 'Drive time',
      value: formatDuration(route.duration_s),
    },
    { label: 'Departs', value: formatDateTime(route.departure) },
    { label: 'Arrives', value: formatDateTime(route.arrival) },
  ]

  return (
    <section className={`${surface.card} ${surface.rise} ${styles.summary}`} aria-label="Trip">
      <div className={styles.heading}>
        <h2 className={styles.places}>
          <span>{trip.origin.label}</span>
          <ArrowRight aria-label="to" />
          <span>{trip.destination.label}</span>
        </h2>
        {!editing && (
          <button type="button" className={styles.action} onClick={onEdit}>
            <Pencil aria-hidden="true" />
            Edit
          </button>
        )}
      </div>
      <p className={styles.meta}>
        {routeName(selectedIndex)} · {request.load_lb.toLocaleString()} lb load · checkpoints every{' '}
        {request.interval_mi} mi · rest stops {request.rest_breaks ? 'on' : 'off'}
      </p>
      <dl className={styles.stats}>
        {stats.map((stat) => (
          <div key={stat.label}>
            <dt>{stat.label}</dt>
            <dd>{stat.value}</dd>
          </div>
        ))}
      </dl>
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.verdict}
          data-passed={plan.verification.passed}
          onClick={onShowChecks}
        >
          <VerdictIcon aria-hidden="true" />
          {passed}/{total} checks passed
        </button>
        <span className={styles.exports}>
          <button
            type="button"
            className={styles.action}
            onClick={onPrint}
            disabled={exporting !== null}
          >
            {exporting === 'print' ? (
              <span className={surface.spinner} aria-hidden="true" />
            ) : (
              <Printer aria-hidden="true" />
            )}
            Print / PDF
          </button>
          <button
            type="button"
            className={styles.action}
            onClick={onExportPng}
            disabled={exporting !== null}
          >
            {exporting === 'png' ? (
              <span className={surface.spinner} aria-hidden="true" />
            ) : (
              <ImageDown aria-hidden="true" />
            )}
            PNG
          </button>
        </span>
      </div>
      {exportError && (
        <p className={styles.exportError} role="alert">
          {exportError}
        </p>
      )}
    </section>
  )
}
