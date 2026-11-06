import { Tab, TabGroup, TabList, TabPanel, TabPanels } from '@headlessui/react'
import { useRef, useState } from 'react'

import type { PlannedTrip, Position, TripPlan } from '../api/types'
import type { ExportKind } from '../hooks/useTripExport'
import surface from '../styles/surface.module.css'
import { CheckpointList } from './CheckpointList'
import { Itinerary } from './Itinerary'
import { RecommendationSummary } from './RecommendationSummary'
import styles from './Results.module.css'
import { RouteCard } from './RouteCard'
import { RouteSwitch } from './RouteSwitch'
import summary from './Summary.module.css'
import { TripSummary } from './TripSummary'
import { VerificationList } from './VerificationList'

const TIME_ZONE = Intl.DateTimeFormat().resolvedOptions().timeZone
const CHECKS_TAB = 3

interface TripResultsProps {
  trip: PlannedTrip
  plan: TripPlan
  refreshing: boolean
  selectedIndex: number
  activeCheckpoint: number | null
  exporting: ExportKind | null
  exportError: string | null
  editing: boolean
  onEdit: () => void
  onPrint: () => void
  onExportPng: () => void
  onSelectRoute: (index: number) => void
  onFocusCheckpoint: (index: number) => void
  onFocusPosition: (position: Position) => void
}

export function TripResults({
  trip,
  plan,
  refreshing,
  selectedIndex,
  activeCheckpoint,
  exporting,
  exportError,
  editing,
  onEdit,
  onPrint,
  onExportPng,
  onSelectRoute,
  onFocusCheckpoint,
  onFocusPosition,
}: TripResultsProps) {
  const [tab, setTab] = useState(0)
  const tabListRef = useRef<HTMLDivElement>(null)
  const route = plan.routes[selectedIndex]
  const { verification } = plan
  const routeSwitch = (
    <RouteSwitch
      count={plan.routes.length}
      selectedIndex={selectedIndex}
      recommendedIndex={plan.recommendation.index}
      onSelect={onSelectRoute}
    />
  )
  const tabs = [
    { label: 'Routes', count: plan.routes.length },
    { label: 'Itinerary', count: null },
    { label: 'Checkpoints', count: route?.checkpoints.length ?? 0 },
    { label: 'Checks', count: verification.passed ? '✓' : '!' },
  ]

  function openTab(index: number) {
    setTab(index)
    tabListRef.current?.scrollIntoView({ block: 'start' })
  }

  return (
    <div className={styles.results} aria-busy={refreshing}>
      <TripSummary
        trip={trip}
        plan={plan}
        selectedIndex={selectedIndex}
        exporting={exporting}
        exportError={exportError}
        editing={editing}
        onEdit={onEdit}
        onPrint={onPrint}
        onExportPng={onExportPng}
        onShowChecks={() => openTab(CHECKS_TAB)}
      />
      <RecommendationSummary plan={plan} />
      <TabGroup selectedIndex={tab} onChange={openTab} className={summary.tabs}>
        <TabList ref={tabListRef} className={summary.tabList}>
          {tabs.map(({ label, count }) => (
            <Tab key={label} className={summary.tab}>
              {label}
              {count !== null && (
                <span
                  className={surface.count}
                  data-failed={(label === 'Checks' && !verification.passed) || undefined}
                >
                  {count}
                </span>
              )}
            </Tab>
          ))}
        </TabList>
        <TabPanels>
          <TabPanel className={summary.panel}>
            {plan.routes.map((planRoute, index) => (
              <RouteCard
                key={index}
                route={planRoute}
                index={index}
                recommended={index === plan.recommendation.index}
                selected={index === selectedIndex}
                onSelect={onSelectRoute}
              />
            ))}
          </TabPanel>
          <TabPanel className={summary.panel}>
            {routeSwitch}
            {route && (
              <Itinerary
                key={selectedIndex}
                trip={trip}
                route={route}
                onFocusPosition={onFocusPosition}
                onFocusCheckpoint={onFocusCheckpoint}
              />
            )}
          </TabPanel>
          <TabPanel className={summary.panel}>
            {routeSwitch}
            {route && (
              <CheckpointList
                key={selectedIndex}
                route={route}
                activeIndex={activeCheckpoint}
                onFocus={onFocusCheckpoint}
              />
            )}
          </TabPanel>
          <TabPanel className={summary.panel}>
            <VerificationList verification={verification} />
          </TabPanel>
        </TabPanels>
      </TabGroup>
      <p className={styles.footnote}>
        Times in {TIME_ZONE}. Truck routing by TomTom, forecasts by Open-Meteo.
      </p>
    </div>
  )
}
