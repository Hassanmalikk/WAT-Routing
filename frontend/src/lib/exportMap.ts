import type { Map as MapInstance } from 'maplibre-gl'

import type { Position, RiskLevel } from '../api/types'
import { RISK_COLORS, RISK_LABELS } from './risk'

export interface MapMarks {
  origin: Position
  destination: Position
  stops: Position[]
}

export interface ImageCaption {
  title: string
  subtitle: string
}

const FONT = "'Inter Variable', system-ui, sans-serif"
const BAND_PX = 84
const LEGEND_PX = 44
const BACKGROUND = '#0a121c'
const TITLE_COLOR = '#f2f7fb'
const MUTED_COLOR = '#8597a6'
const ORIGIN_COLOR = '#4fd8c8'
const DESTINATION_COLOR = '#ff8a3d'
const STOP_COLOR = '#4b3b8f'
const REVOKE_DELAY_MS = 10_000

function context(canvas: HTMLCanvasElement): CanvasRenderingContext2D {
  const context2d = canvas.getContext('2d')
  if (!context2d) throw new Error('Canvas 2D is not available in this browser.')
  return context2d
}

function drawMarks(target: CanvasRenderingContext2D, map: MapInstance, marks: MapMarks) {
  const ratio = target.canvas.width / map.getCanvas().clientWidth
  const dot = (position: Position, radius: number, fill: string, square: boolean) => {
    const { x, y } = map.project([position.lon, position.lat])
    target.beginPath()
    if (square) target.roundRect(x - radius, y - radius, radius * 2, radius * 2, 3)
    else target.arc(x, y, radius, 0, Math.PI * 2)
    target.fillStyle = fill
    target.fill()
    target.lineWidth = 3
    target.strokeStyle = '#ffffff'
    target.stroke()
  }
  target.save()
  target.scale(ratio, ratio)
  for (const stop of marks.stops) dot(stop, 6, STOP_COLOR, false)
  dot(marks.origin, 8, ORIGIN_COLOR, false)
  dot(marks.destination, 8, DESTINATION_COLOR, true)
  target.restore()
}

export function captureMap(map: MapInstance, marks: MapMarks): Promise<HTMLCanvasElement> {
  return new Promise((resolve, reject) => {
    map.once('render', () => {
      try {
        const source = map.getCanvas()
        const full = document.createElement('canvas')
        full.width = source.width
        full.height = source.height
        const fullContext = context(full)
        fullContext.drawImage(source, 0, 0)
        drawMarks(fullContext, map, marks)

        const ratio = source.width / source.clientWidth
        const cropX = Math.min(Math.round((map.getPadding().left ?? 0) * ratio), source.width - 1)
        const cropped = document.createElement('canvas')
        cropped.width = source.width - cropX
        cropped.height = source.height
        context(cropped).drawImage(
          full,
          cropX,
          0,
          cropped.width,
          cropped.height,
          0,
          0,
          cropped.width,
          cropped.height,
        )
        resolve(cropped)
      } catch (error) {
        reject(error instanceof Error ? error : new Error(String(error)))
      }
    })
    map.triggerRepaint()
  })
}

export function captionImage(
  snapshot: HTMLCanvasElement,
  caption: ImageCaption,
): HTMLCanvasElement {
  const scale = Math.max(1, Math.round(snapshot.width / 1200))
  const band = BAND_PX * scale
  const legend = LEGEND_PX * scale
  const canvas = document.createElement('canvas')
  canvas.width = snapshot.width
  canvas.height = snapshot.height + band + legend
  const target = context(canvas)
  target.fillStyle = BACKGROUND
  target.fillRect(0, 0, canvas.width, canvas.height)
  target.drawImage(snapshot, 0, band)

  const pad = 24 * scale
  target.textBaseline = 'alphabetic'
  target.fillStyle = TITLE_COLOR
  target.font = `700 ${24 * scale}px ${FONT}`
  target.fillText(caption.title, pad, 40 * scale, canvas.width - pad * 2)
  target.fillStyle = MUTED_COLOR
  target.font = `500 ${15 * scale}px ${FONT}`
  target.fillText(caption.subtitle, pad, 66 * scale, canvas.width - pad * 2)

  let x = pad
  const y = band + snapshot.height + legend / 2
  target.textBaseline = 'middle'
  target.font = `500 ${13 * scale}px ${FONT}`
  for (const level of [0, 1, 2, 3, 4] as RiskLevel[]) {
    target.fillStyle = RISK_COLORS[level]
    target.beginPath()
    target.arc(x + 5 * scale, y, 5 * scale, 0, Math.PI * 2)
    target.fill()
    target.fillStyle = TITLE_COLOR
    target.fillText(RISK_LABELS[level], x + 16 * scale, y)
    x += 16 * scale + target.measureText(RISK_LABELS[level]).width + 22 * scale
  }
  return canvas
}

export function downloadCanvas(canvas: HTMLCanvasElement, filename: string): Promise<void> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('The image could not be created.'))
        return
      }
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), REVOKE_DELAY_MS)
      resolve()
    }, 'image/png')
  })
}

export function fileSlug(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
}
