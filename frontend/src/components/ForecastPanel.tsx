import { ChevronDown } from 'lucide-react'
import { memo, useDeferredValue, useEffect, useId, useMemo, useState } from 'react'
import { Layer, Source } from 'react-map-gl/maplibre'

import type { Heatmap } from '../api/types'
import { formatDateTime } from '../lib/format'
import {
  HEATMAP_LEGEND_COLORS,
  HEATMAP_METRICS,
  type HeatmapMetric,
  heatmapColor,
  heatmapFeatures,
  heatmapRadius,
  hourProperty,
} from '../lib/heatmap'
import styles from './Map.module.css'

const PLAY_STEP_MS = 450
const HEATMAP_OPACITY = 0.7

interface ForecastPanelProps {
  heatmap: Heatmap
  beforeId: string
}

export const ForecastPanel = memo(function ForecastPanel({
  heatmap,
  beforeId,
}: ForecastPanelProps) {
  const lastHour = heatmap.hours.length - 1
  const [hour, setHour] = useState(0)
  const [metric, setMetric] = useState<HeatmapMetric>('risk')
  const [visible, setVisible] = useState(true)
  const [playing, setPlaying] = useState(false)
  const [collapsed, setCollapsed] = useState(false)
  const renderedHour = useDeferredValue(hour)
  const sliderId = useId()
  const bodyId = useId()

  const data = useMemo(() => heatmapFeatures(heatmap, metric), [heatmap, metric])
  const radius = useMemo(() => heatmapRadius(heatmap), [heatmap])
  const color = useMemo(() => heatmapColor(metric), [metric])

  const animating = playing && hour < lastHour

  useEffect(() => {
    if (!animating) return
    const timer = window.setTimeout(() => setHour((current) => current + 1), PLAY_STEP_MS)
    return () => window.clearTimeout(timer)
  }, [animating, hour])

  function togglePlay() {
    if (!animating && hour >= lastHour) setHour(0)
    setPlaying(!animating)
  }

  const moment = heatmap.hours[hour]
  const { legend } = HEATMAP_METRICS[metric]

  return (
    <>
      <Source id="forecast" type="geojson" data={data}>
        <Layer
          id="forecast-heatmap"
          type="heatmap"
          beforeId={beforeId}
          layout={{ visibility: visible ? 'visible' : 'none' }}
          paint={{
            'heatmap-weight': ['get', hourProperty(renderedHour)],
            'heatmap-radius': radius,
            'heatmap-intensity': 1,
            'heatmap-color': color,
            'heatmap-opacity': HEATMAP_OPACITY,
          }}
        />
      </Source>
      <section
        className={styles.forecast}
        data-collapsed={collapsed || undefined}
        aria-label="Weather forecast heatmap"
      >
        <div className={styles.forecastTop}>
          <div className={styles.metricSwitch} role="radiogroup" aria-label="Heatmap layer">
            {(Object.keys(HEATMAP_METRICS) as HeatmapMetric[]).map((key) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={metric === key}
                onClick={() => setMetric(key)}
              >
                {HEATMAP_METRICS[key].label}
              </button>
            ))}
          </div>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={visible}
              onChange={(event) => setVisible(event.target.checked)}
            />
            Show
          </label>
          <button
            type="button"
            className={styles.collapseForecast}
            onClick={() => setCollapsed(!collapsed)}
            aria-expanded={!collapsed}
            aria-controls={bodyId}
            aria-label={collapsed ? 'Expand forecast controls' : 'Collapse forecast controls'}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            <ChevronDown />
          </button>
        </div>
        <div id={bodyId} className={styles.forecastBody} inert={collapsed}>
          <div className={styles.forecastInner}>
            <div className={styles.sliderRow}>
              <button
                type="button"
                className={styles.play}
                onClick={togglePlay}
                aria-label={animating ? 'Pause forecast animation' : 'Play forecast animation'}
              >
                <svg viewBox="0 0 16 16" aria-hidden="true">
                  {animating ? <path d="M4 3h3v10H4zM9 3h3v10H9z" /> : <path d="M4 2l10 6-10 6z" />}
                </svg>
              </button>
              <div className={styles.sliderBody}>
                <label htmlFor={sliderId} className={styles.sliderLabel}>
                  <strong>+{hour} h</strong>
                  {moment && <span>{formatDateTime(moment)}</span>}
                </label>
                <input
                  id={sliderId}
                  className={styles.slider}
                  style={{ '--progress': `${(hour / Math.max(lastHour, 1)) * 100}%` }}
                  type="range"
                  min={0}
                  max={lastHour}
                  step={1}
                  value={hour}
                  onChange={(event) => {
                    setPlaying(false)
                    setHour(Number(event.target.value))
                  }}
                  aria-valuetext={`${hour} hours after departure`}
                />
              </div>
            </div>
            <div className={styles.legend} aria-hidden="true">
              {legend.map((label, index) => (
                <span key={label}>
                  <i style={{ background: HEATMAP_LEGEND_COLORS[index] }} />
                  {label}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>
    </>
  )
})
