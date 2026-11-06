import { useSyncExternalStore } from 'react'

import type { Place } from '../api/types'
import { readStorage, writeStorage } from './storage'

const STORAGE_KEY = 'recent-places'
const MAX_RECENT_PLACES = 6

const listeners = new Set<() => void>()
let snapshot: Place[] | null = null

function isPlace(value: unknown): value is Place {
  if (typeof value !== 'object' || value === null) return false
  const { label, position } = value as Partial<Place>
  return (
    typeof label === 'string' &&
    typeof position?.lat === 'number' &&
    typeof position.lon === 'number'
  )
}

export function parseRecentPlaces(raw: string | null): Place[] {
  if (!raw) return []
  try {
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter(isPlace).slice(0, MAX_RECENT_PLACES) : []
  } catch {
    return []
  }
}

export function mergeRecentPlaces(used: Place[], current: Place[]): Place[] {
  const merged = new Map<string, Place>()
  for (const place of [...used, ...current]) {
    if (!merged.has(place.label)) merged.set(place.label, place)
  }
  return [...merged.values()].slice(0, MAX_RECENT_PLACES)
}

function getSnapshot(): Place[] {
  snapshot ??= parseRecentPlaces(readStorage(STORAGE_KEY))
  return snapshot
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function rememberPlaces(used: Place[]) {
  snapshot = mergeRecentPlaces(used, getSnapshot())
  writeStorage(STORAGE_KEY, JSON.stringify(snapshot))
  for (const listener of listeners) listener()
}

export function useRecentPlaces(): Place[] {
  return useSyncExternalStore(subscribe, getSnapshot)
}
