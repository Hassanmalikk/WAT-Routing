import { describe, expect, it } from 'vitest'

import type { Place } from '../api/types'
import { mergeRecentPlaces, parseRecentPlaces } from './recentPlaces'

function place(label: string): Place {
  return { label, position: { lat: 40, lon: -100 } }
}

describe('recent places', () => {
  it('ignores missing, corrupt and malformed storage', () => {
    expect(parseRecentPlaces(null)).toEqual([])
    expect(parseRecentPlaces('{oops')).toEqual([])
    expect(parseRecentPlaces('{"label":"x"}')).toEqual([])
    expect(parseRecentPlaces(JSON.stringify([place('Denver, CO'), { label: 1 }]))).toEqual([
      place('Denver, CO'),
    ])
  })

  it('puts the latest places first without duplicates, capped at six', () => {
    const current = ['A', 'B', 'C', 'D', 'E', 'F'].map(place)
    const merged = mergeRecentPlaces([place('C'), place('Z')], current)
    expect(merged.map((item) => item.label)).toEqual(['C', 'Z', 'A', 'B', 'D', 'E'])
  })
})
