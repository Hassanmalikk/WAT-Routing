import type { Place, TripPlan, TripRequest } from './types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const FALLBACK_MESSAGE = 'Something went wrong. Please try again.'

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
  })
  if (response.ok) {
    return (await response.json()) as T
  }
  const body: unknown = await response.json().catch(() => null)
  const detail =
    body !== null && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : FALLBACK_MESSAGE
  throw new ApiError(
    response.status,
    response.status === 429 ? 'Too many requests. Please wait a moment.' : detail,
  )
}

export function searchPlaces(query: string, signal: AbortSignal): Promise<Place[]> {
  return request(`/api/places?${new URLSearchParams({ q: query })}`, { signal })
}

export function planTrip(trip: TripRequest, signal: AbortSignal): Promise<TripPlan> {
  return request('/api/trips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(trip),
    signal,
  })
}
