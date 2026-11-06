import { hashKey } from '@tanstack/react-query'
import { ChevronUp, Moon, Route as RouteIcon, Sun } from 'lucide-react'
import { useRef, useState } from 'react'
import { MapProvider, useMap } from 'react-map-gl/maplibre'

import styles from './App.module.css'
import { useTripPlan } from './api/queries'
import type { PlannedTrip, Position, TripPlan } from './api/types'
import { ErrorCard, PlanSkeleton, Welcome } from './components/PanelStates'
import { PrintReport } from './components/PrintReport'
import { TripForm } from './components/TripForm'
import { MAP_ID, TripMap } from './components/TripMap'
import { TripResults } from './components/TripResults'
import { useCoveredWidth } from './hooks/useCoveredWidth'
import { useTheme } from './hooks/useTheme'
import { useTripExport } from './hooks/useTripExport'

const FOCUS_MIN_ZOOM = 7

interface Selection {
  plan: TripPlan
  route: number
  checkpoint: number | null
}

function Planner() {
  const [trip, setTrip] = useState<PlannedTrip | null>(null)
  const { data: plan, error, isFetching, refetch } = useTripPlan(trip?.request ?? null)
  const [selection, setSelection] = useState<Selection | null>(null)
  const [minimized, setMinimized] = useState(false)
  const [editing, setEditing] = useState(false)
  const [theme, toggleTheme] = useTheme()
  const { [MAP_ID]: map } = useMap()
  const panelRef = useRef<HTMLElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<HTMLElement>(null)
  const coveredWidth = useCoveredWidth(panelRef, mapRef)

  const current = plan && selection?.plan === plan ? selection : null
  const selectedIndex = current?.route ?? plan?.recommendation.index ?? 0
  const activeCheckpoint = current?.checkpoint ?? null
  const route = plan?.routes[selectedIndex]
  const tripExport = useTripExport(trip, plan, selectedIndex)
  const formCollapsed = plan !== undefined && !editing

  function submit(next: PlannedTrip) {
    setEditing(false)
    if (trip && hashKey([trip.request]) === hashKey([next.request])) void refetch()
    else setTrip(next)
  }

  function editTrip() {
    setEditing(true)
    scrollRef.current?.scrollTo({ top: 0 })
  }

  function selectRoute(index: number) {
    if (plan) setSelection({ plan, route: index, checkpoint: null })
  }

  function activateCheckpoint(index: number | null) {
    if (plan) setSelection({ plan, route: selectedIndex, checkpoint: index })
  }

  function focusPosition(position: Position) {
    mapRef.current?.scrollIntoView({ block: 'nearest' })
    map?.easeTo({
      center: [position.lon, position.lat],
      zoom: Math.max(map.getZoom(), FOCUS_MIN_ZOOM),
    })
  }

  function focusCheckpoint(index: number) {
    activateCheckpoint(index)
    const checkpoint = route?.checkpoints[index]
    if (checkpoint) focusPosition(checkpoint.position)
  }

  const nextTheme = theme === 'dark' ? 'light' : 'dark'
  const ThemeIcon = theme === 'dark' ? Sun : Moon

  return (
    <div className={styles.app}>
      <aside ref={panelRef} className={styles.panel} data-minimized={minimized || undefined}>
        <header className={styles.header}>
          <span className={styles.logo} aria-hidden="true">
            <RouteIcon />
          </span>
          <div className={styles.title}>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Safest route by forecast, load and time</p>
          </div>
          <button
            type="button"
            className={styles.iconButton}
            onClick={toggleTheme}
            aria-label={`Switch to ${nextTheme} theme`}
            title={`Switch to ${nextTheme} theme`}
          >
            <ThemeIcon />
          </button>
          <button
            type="button"
            className={`${styles.iconButton} ${styles.minimize}`}
            onClick={() => setMinimized(!minimized)}
            aria-expanded={!minimized}
            aria-controls="planner-panel"
            aria-label={minimized ? 'Expand panel' : 'Minimize panel'}
            title={minimized ? 'Expand panel' : 'Minimize panel'}
          >
            <ChevronUp />
          </button>
        </header>
        <div id="planner-panel" ref={scrollRef} className={styles.scroll} hidden={minimized}>
          <div
            className={styles.formSlot}
            data-collapsed={formCollapsed || undefined}
            inert={formCollapsed}
          >
            <div className={styles.formSlotBody}>
              <TripForm isPlanning={isFetching} onSubmit={submit} />
            </div>
          </div>
          {isFetching && !plan && <PlanSkeleton />}
          {error && !isFetching && (
            <ErrorCard message={error.message} onRetry={() => void refetch()} />
          )}
          {!trip && <Welcome />}
          {plan && trip && (
            <TripResults
              trip={trip}
              plan={plan}
              refreshing={isFetching}
              selectedIndex={selectedIndex}
              activeCheckpoint={activeCheckpoint}
              exporting={tripExport.exporting}
              exportError={tripExport.exportError}
              editing={editing}
              onEdit={editTrip}
              onPrint={() => void tripExport.printReport()}
              onExportPng={() => void tripExport.exportPng()}
              onSelectRoute={selectRoute}
              onFocusCheckpoint={focusCheckpoint}
              onFocusPosition={focusPosition}
            />
          )}
        </div>
      </aside>
      <main ref={mapRef} className={styles.map}>
        <TripMap
          plan={plan}
          theme={theme}
          coveredLeft={coveredWidth}
          selectedIndex={selectedIndex}
          activeCheckpoint={activeCheckpoint}
          onSelectRoute={selectRoute}
          onActivateCheckpoint={activateCheckpoint}
        />
      </main>
      {plan && trip && (
        <PrintReport
          trip={trip}
          plan={plan}
          selectedIndex={selectedIndex}
          snapshot={tripExport.snapshot}
        />
      )}
    </div>
  )
}

export default function App() {
  return (
    <MapProvider>
      <Planner />
    </MapProvider>
  )
}
