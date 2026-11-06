import type { PlannedTrip, TripPlan } from '../api/types'
import { formatDateTime, formatDuration, formatMiles, formatTime } from '../lib/format'
import { buildItinerary, type ItineraryEvent } from '../lib/itinerary'
import { RISK_LABELS } from '../lib/risk'
import { explainRecommendation, routeName } from '../lib/routes'
import styles from './PrintReport.module.css'

const TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone

interface PrintReportProps {
  trip: PlannedTrip
  plan: TripPlan
  selectedIndex: number
  snapshot: string | null
}

function eventLabel(event: ItineraryEvent, trip: PlannedTrip): string {
  switch (event.kind) {
    case 'depart':
      return `Depart ${trip.origin.label}`
    case 'arrive':
      return `Arrive ${trip.destination.label}`
    case 'drive':
      return `Drive ${formatMiles(event.miles)} (${formatDuration(event.duration_s)})`
    case 'weather':
      return event.reason
    case 'break':
      return `30 min break until ${formatTime(event.end)}`
    case 'rest':
      return `10 h rest until ${formatDateTime(event.end)}`
  }
}

export function PrintReport({ trip, plan, selectedIndex, snapshot }: PrintReportProps) {
  const route = plan.routes[selectedIndex]
  if (!route) return null
  const { request } = trip
  const name = routeName(selectedIndex)
  const passed = plan.verification.checks.filter((check) => check.passed).length

  return (
    <article className={styles.report} aria-hidden="true">
      <header>
        <h1>
          {trip.origin.label} → {trip.destination.label}
        </h1>
        <p>
          Departs {formatDateTime(request.departure)} · {request.load_lb.toLocaleString()} lb load ·
          checkpoints every {request.interval_mi} mi · hours-of-service stops{' '}
          {request.rest_breaks ? 'on' : 'off'}
        </p>
      </header>

      {snapshot && <img src={snapshot} alt="" className={styles.map} />}

      <section>
        <h2>Recommendation: {routeName(plan.recommendation.index)}</h2>
        <p>{explainRecommendation(plan.routes, plan.recommendation)}</p>
        <p>
          Independent checks: {passed} of {plan.verification.checks.length} passed.
        </p>
      </section>

      <section>
        <h2>Route comparison</h2>
        <table>
          <thead>
            <tr>
              <th>Route</th>
              <th>Distance</th>
              <th>Total time</th>
              <th>Arrival</th>
              <th>No travel</th>
              <th>Severe</th>
              <th>High</th>
              <th>Avg risk</th>
            </tr>
          </thead>
          <tbody>
            {plan.routes.map((planRoute, index) => (
              <tr key={index}>
                <td>
                  {routeName(index)}
                  {index === plan.recommendation.index && ' (safest)'}
                </td>
                <td>{formatMiles(planRoute.distance_mi)}</td>
                <td>{formatDuration(planRoute.duration_s)}</td>
                <td>{formatDateTime(planRoute.arrival)}</td>
                <td>{formatMiles(planRoute.summary.no_travel_mi)}</td>
                <td>{formatMiles(planRoute.summary.severe_mi)}</td>
                <td>{formatMiles(planRoute.summary.high_mi)}</td>
                <td>{planRoute.summary.average_risk.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>{name} itinerary</h2>
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Mile</th>
              <th>Event</th>
            </tr>
          </thead>
          <tbody>
            {buildItinerary(route).map((event) => (
              <tr key={`${event.kind}-${event.time}-${event.mile}`}>
                <td>{formatDateTime(event.time)}</td>
                <td>{Math.round(event.mile)}</td>
                <td>{eventLabel(event, trip)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>{name} checkpoints</h2>
        <table>
          <thead>
            <tr>
              <th>Mile</th>
              <th>ETA</th>
              <th>Wind mph</th>
              <th>Gust mph</th>
              <th>Rain in/hr</th>
              <th>Snow in/hr</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((checkpoint) => (
              <tr key={checkpoint.mile}>
                <td>{Math.round(checkpoint.mile)}</td>
                <td>{formatDateTime(checkpoint.eta)}</td>
                <td>{Math.round(checkpoint.conditions.wind_mph)}</td>
                <td>{Math.round(checkpoint.conditions.gust_mph)}</td>
                <td>{checkpoint.conditions.rain_in_hr.toFixed(2)}</td>
                <td>{checkpoint.conditions.snow_in_hr.toFixed(2)}</td>
                <td>
                  {RISK_LABELS[checkpoint.risk.level]}
                  {checkpoint.risk.load_adjusted && ' (load)'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Independent checks</h2>
        <ul>
          {plan.verification.checks.map((check) => (
            <li key={check.key}>
              <strong>{check.passed ? 'Passed' : 'Failed'}:</strong> {check.title}. {check.detail}
            </li>
          ))}
        </ul>
      </section>

      <footer>Times in {TIME_ZONE}. Truck routing by TomTom, forecasts by Open-Meteo.</footer>
    </article>
  )
}
