import {
  Combobox,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
  Field,
  Label,
} from '@headlessui/react'
import { Clock, type LucideIcon, MapPin } from 'lucide-react'
import { useState } from 'react'

import { MIN_PLACE_QUERY_LENGTH, usePlaces } from '../api/queries'
import type { Place } from '../api/types'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useRecentPlaces } from '../lib/recentPlaces'
import surface from '../styles/surface.module.css'
import styles from './Form.module.css'

const SEARCH_DEBOUNCE_MS = 250

interface PlaceFieldProps {
  label: string
  icon: LucideIcon
  tone: 'origin' | 'destination'
  placeholder: string
  value: Place | null
  onChange: (place: Place | null) => void
  error: string | null
}

function samePlace(a: Place | null, b: Place | null): boolean {
  return a?.label === b?.label
}

function splitLabel(label: string): [string, string] {
  const separator = label.indexOf(', ')
  return separator === -1 ? [label, ''] : [label.slice(0, separator), label.slice(separator + 2)]
}

export function PlaceField({
  label,
  icon: Icon,
  tone,
  placeholder,
  value,
  onChange,
  error,
}: PlaceFieldProps) {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, SEARCH_DEBOUNCE_MS)
  const places = usePlaces(debouncedQuery)
  const recents = useRecentPlaces()
  const searchable = query.trim().length >= MIN_PLACE_QUERY_LENGTH
  const showingRecents = query.trim() === '' && recents.length > 0
  const suggestions = searchable ? (places.data ?? []) : showingRecents ? recents : []
  const OptionIcon = showingRecents ? Clock : MapPin
  const searching = searchable && (places.isFetching || debouncedQuery !== query)

  let status: string | null = null
  if (!searchable) status = query.trim() === '' ? null : 'Type at least 2 characters'
  else if (places.isError) status = places.error.message
  else if (searching && suggestions.length === 0) status = 'Searching…'
  else if (suggestions.length === 0) status = 'No matching places'

  return (
    <Field className={styles.field}>
      <Label className={styles.label}>{label}</Label>
      <Combobox
        value={value}
        onChange={onChange}
        onClose={() => setQuery('')}
        by={samePlace}
        immediate
      >
        <div className={styles.control} data-tone={tone}>
          <Icon className={styles.icon} aria-hidden="true" />
          <ComboboxInput
            className={styles.input}
            placeholder={placeholder}
            autoComplete="off"
            aria-invalid={error !== null}
            displayValue={(place: Place | null) => place?.label ?? ''}
            onChange={(event) => setQuery(event.target.value)}
          />
          {searching && (
            <span className={`${surface.spinner} ${styles.searching}`} aria-hidden="true" />
          )}
        </div>
        <ComboboxOptions anchor="bottom start" transition className={styles.options}>
          {status && <div className={styles.optionStatus}>{status}</div>}
          {showingRecents && <div className={styles.optionGroup}>Recent</div>}
          {suggestions.map((place) => {
            const [name, detail] = splitLabel(place.label)
            return (
              <ComboboxOption key={place.label} value={place} className={styles.option}>
                <OptionIcon aria-hidden="true" />
                <span>
                  <span className={styles.optionName}>{name}</span>
                  {detail && <span className={styles.optionDetail}>{detail}</span>}
                </span>
              </ComboboxOption>
            )
          })}
        </ComboboxOptions>
      </Combobox>
      {error && <p className={styles.error}>{error}</p>}
    </Field>
  )
}
