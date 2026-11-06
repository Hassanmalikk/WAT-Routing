import 'maplibre-gl/dist/maplibre-gl.css'

import type { FeatureCollection, LineString, Point } from 'geojson'
import type { ExpressionSpecification, Map as MapInstance } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useMemo, useState } from 'react'
import Map, {
  Layer,
  type MapLayerMouseEvent,
  Marker,
  NavigationControl,
  Popup,
  Source,
  useMap,
} from 'react-map-gl/maplibre'

import type { TripPlan } from '../api/types'
import type { Theme } from '../hooks/useTheme'
import { formatDateTime, formatDuration } from '../lib/format'
import { riskColorExpression } from '../lib/risk'
import { routeBounds } from '../lib/routes'
import { CheckpointDetails } from './CheckpointDetails'
import { ForecastPanel } from './ForecastPanel'
import styles from './Map.module.css'

const mapLib = import('maplibre-gl').then((maplibre) => {
  maplibre.setWorkerUrl(maplibreWorkerUrl)
  return maplibre
})

export const MAP_ID = 'trip'
const MAP_STYLES: Record<Theme, string> = {
  light: 'https://tiles.openfreemap.org/styles/positron',
  dark: 'https://tiles.openfreemap.org/styles/dark',
}
const INITIAL_VIEW = { longitude: -98.5, latitude: 39.5, zoom: 3.4 }
const FIT_PADDING = { top: 48, bottom: 200, left: 48, right: 48 }
const CASING_LAYER = 'route-casing'
const ROUTE_LAYER = 'route-line'
const CHECKPOINT_LAYER = 'checkpoints'
const INTERACTIVE_LAYERS = [CHECKPOINT_LAYER, ROUTE_LAYER]

interface TripMapProps {
  plan: TripPlan | undefined
  theme: Theme
  coveredLeft: number
  selectedIndex: number
  activeCheckpoint: number | null
  onSelectRoute: (index: number) => void
  onActivateCheckpoint: (index: number | null) => void
}

const BLANK_ICON = { width: 1, height: 1, data: new Uint8Array(4) }

function firstLabelLayer(map: MapInstance): string | undefined {
  return map.getLayersOrder().find((id) => map.getLayer(id)?.type === 'symbol')
}

function bySelection(
  selectedIndex: number,
  selected: number,
  other: number,
): ExpressionSpecification {
  return ['case', ['==', ['get', 'route'], selectedIndex], selected, other]
}

export function TripMap({
  plan,
  theme,
  coveredLeft,
  selectedIndex,
  activeCheckpoint,
  onSelectRoute,
  onActivateCheckpoint,
}: TripMapProps) {
  const { [MAP_ID]: map } = useMap()
  const [labelLayerId, setLabelLayerId] = useState<string>()
  const [hovering, setHovering] = useState(false)
  const route = plan?.routes[selectedIndex]

  useEffect(() => {
    const instance = map?.getMap()
    instance?.setMissingStyleImageResolver((id) => {
      if (!instance.hasImage(id)) instance.addImage(id, BLANK_ICON)
    })
  }, [map])

  useEffect(() => {
    map?.setPadding({ top: 0, right: 0, bottom: 0, left: coveredLeft })
  }, [map, coveredLeft])

  useEffect(() => {
    const bounds = plan && routeBounds(plan.routes)
    if (map && bounds) map.fitBounds(bounds, { padding: FIT_PADDING, duration: 900 })
  }, [map, plan])

  const routeLines = useMemo<FeatureCollection<LineString>>(
    () => ({
      type: 'FeatureCollection',
      features: (plan?.routes ?? []).flatMap((planRoute, routeIndex) =>
        planRoute.segments.map((segment) => ({
          type: 'Feature',
          properties: { route: routeIndex, level: segment.level },
          geometry: { type: 'LineString', coordinates: segment.coordinates },
        })),
      ),
    }),
    [plan],
  )

  const checkpoints = useMemo<FeatureCollection<Point>>(
    () => ({
      type: 'FeatureCollection',
      features: (route?.checkpoints ?? []).map((checkpoint, index) => ({
        type: 'Feature',
        properties: { index, level: checkpoint.risk.level },
        geometry: {
          type: 'Point',
          coordinates: [checkpoint.position.lon, checkpoint.position.lat],
        },
      })),
    }),
    [route],
  )

  function handleClick(event: MapLayerMouseEvent) {
    const feature = event.features?.[0]
    if (!feature) {
      onActivateCheckpoint(null)
    } else if (feature.layer.id === CHECKPOINT_LAYER) {
      onActivateCheckpoint(Number(feature.properties.index))
    } else {
      onSelectRoute(Number(feature.properties.route))
    }
  }

  const active = activeCheckpoint === null ? undefined : route?.checkpoints[activeCheckpoint]
  const origin = route?.checkpoints[0]
  const destination = route?.checkpoints.at(-1)

  return (
    <Map
      id={MAP_ID}
      mapLib={mapLib}
      initialViewState={INITIAL_VIEW}
      mapStyle={MAP_STYLES[theme]}
      interactiveLayerIds={INTERACTIVE_LAYERS}
      cursor={hovering ? 'pointer' : 'grab'}
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
      onClick={handleClick}
      onStyleData={(event) => setLabelLayerId(firstLabelLayer(event.target))}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <Source id="routes" type="geojson" data={routeLines}>
        <Layer
          id={CASING_LAYER}
          type="line"
          beforeId={labelLayerId}
          layout={{
            'line-join': 'round',
            'line-cap': 'round',
            'line-sort-key': bySelection(selectedIndex, 1, 0),
          }}
          paint={{
            'line-color': '#ffffff',
            'line-width': bySelection(selectedIndex, 10, 6),
            'line-opacity': bySelection(selectedIndex, 1, 0.8),
          }}
        />
        <Layer
          id={ROUTE_LAYER}
          type="line"
          beforeId={labelLayerId}
          layout={{
            'line-join': 'round',
            'line-cap': 'round',
            'line-sort-key': bySelection(selectedIndex, 1, 0),
          }}
          paint={{
            'line-color': riskColorExpression('level'),
            'line-width': bySelection(selectedIndex, 6, 3),
            'line-opacity': bySelection(selectedIndex, 1, 0.5),
          }}
        />
      </Source>
      <Source id="checkpoints" type="geojson" data={checkpoints}>
        <Layer
          id={CHECKPOINT_LAYER}
          type="circle"
          paint={{
            'circle-color': riskColorExpression('level'),
            'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 4, 10, 8],
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': 2,
          }}
        />
      </Source>
      {plan && <ForecastPanel heatmap={plan.heatmap} beforeId={CASING_LAYER} />}
      {origin && (
        <Marker longitude={origin.position.lon} latitude={origin.position.lat}>
          <span className={styles.endpoint} data-kind="origin" role="img" aria-label="Origin" />
        </Marker>
      )}
      {destination && (
        <Marker longitude={destination.position.lon} latitude={destination.position.lat}>
          <span
            className={styles.endpoint}
            data-kind="destination"
            role="img"
            aria-label="Destination"
          />
        </Marker>
      )}
      {route?.stops.map((stop) => (
        <Marker key={stop.start} longitude={stop.position.lon} latitude={stop.position.lat}>
          <span
            className={styles.stop}
            data-kind={stop.kind}
            title={`${formatDateTime(stop.start)} – ${formatDateTime(stop.end)}`}
          >
            {stop.kind === 'rest' ? 'Rest' : 'Break'}
            <small>{formatDuration((Date.parse(stop.end) - Date.parse(stop.start)) / 1000)}</small>
          </span>
        </Marker>
      ))}
      {active && (
        <Popup
          longitude={active.position.lon}
          latitude={active.position.lat}
          offset={12}
          closeOnClick={false}
          onClose={() => onActivateCheckpoint(null)}
          maxWidth="300px"
          className={styles.popup}
        >
          <CheckpointDetails checkpoint={active} />
        </Popup>
      )}
      {!plan && <p className={styles.emptyHint}>Plan a trip to see routes and weather.</p>}
    </Map>
  )
}
