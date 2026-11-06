import { keepPreviousData, skipToken, useQuery } from '@tanstack/react-query'

import { planTrip, searchPlaces } from './client'
import type { TripRequest } from './types'

export const MIN_PLACE_QUERY_LENGTH = 2

export function usePlaces(query: string) {
  const normalized = query.trim().replace(/\s+/g, ' ').toLowerCase()
  return useQuery({
    queryKey: ['places', normalized],
    queryFn:
      normalized.length >= MIN_PLACE_QUERY_LENGTH
        ? ({ signal }) => searchPlaces(normalized, signal)
        : skipToken,
    staleTime: Infinity,
    gcTime: 60 * 60_000,
    placeholderData: keepPreviousData,
  })
}

export function useTripPlan(trip: TripRequest | null) {
  return useQuery({
    queryKey: ['trip', trip],
    queryFn: trip ? ({ signal }) => planTrip(trip, signal) : skipToken,
    staleTime: 15 * 60_000,
    retry: false,
  })
}
