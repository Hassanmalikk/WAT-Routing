import { useState } from 'react'
import { flushSync } from 'react-dom'
import { useMap } from 'react-map-gl/maplibre'

import type { PlannedTrip, Route, TripPlan } from '../api/types'
import { MAP_ID } from '../components/TripMap'
import { captionImage, captureMap, downloadCanvas, fileSlug, type MapMarks } from '../lib/exportMap'
import { formatDateTime, formatDuration, formatMiles } from '../lib/format'
import { routeName } from '../lib/routes'

export type ExportKind = 'print' | 'png'

export interface MapSnapshot {
  plan: TripPlan
  route: number
  url: string
}

function marks(route: Route): MapMarks | null {
  const origin = route.checkpoints[0]
  const destination = route.checkpoints.at(-1)
  if (!origin || !destination) return null
  return {
    origin: origin.position,
    destination: destination.position,
    stops: route.stops.map((stop) => stop.position),
  }
}

async function decoded(url: string): Promise<void> {
  const image = new Image()
  image.src = url
  await image.decode()
}

export function useTripExport(trip: PlannedTrip | null, plan: TripPlan | undefined, index: number) {
  const { [MAP_ID]: map } = useMap()
  const [exporting, setExporting] = useState<ExportKind | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<MapSnapshot | null>(null)
  const route = plan?.routes[index]

  async function capture(): Promise<HTMLCanvasElement> {
    const routeMarks = route && marks(route)
    if (!map || !routeMarks) throw new Error('The map is not ready yet.')
    return captureMap(map.getMap(), routeMarks)
  }

  async function run(kind: ExportKind, task: () => Promise<void>) {
    setExporting(kind)
    setExportError(null)
    try {
      await task()
    } catch (error) {
      setExportError(error instanceof Error ? error.message : 'Export failed.')
    } finally {
      setExporting(null)
    }
  }

  function printReport() {
    return run('print', async () => {
      if (!plan) return
      const url = await capture()
        .then((canvas) => canvas.toDataURL('image/png'))
        .catch(() => null)
      if (url) await decoded(url)
      flushSync(() => setSnapshot(url ? { plan, route: index, url } : null))
      window.print()
    })
  }

  function exportPng() {
    return run('png', async () => {
      if (!trip || !plan || !route) return
      const title = `${trip.origin.label} → ${trip.destination.label}`
      const recommended = index === plan.recommendation.index ? ' (recommended)' : ''
      const subtitle = [
        `${routeName(index)}${recommended}`,
        formatMiles(route.distance_mi),
        formatDuration(route.duration_s),
        `departs ${formatDateTime(route.departure)}`,
        `${trip.request.load_lb.toLocaleString()} lb`,
      ].join(' · ')
      const image = captionImage(await capture(), { title, subtitle })
      await downloadCanvas(image, `${fileSlug(title)}-${fileSlug(routeName(index))}.png`)
    })
  }

  const currentSnapshot =
    snapshot && snapshot.plan === plan && snapshot.route === index ? snapshot.url : null

  return { exporting, exportError, snapshot: currentSnapshot, printReport, exportPng }
}
