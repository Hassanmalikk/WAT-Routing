import { Field, Label, Radio, RadioGroup, Switch } from '@headlessui/react'
import { ArrowUpDown, Flag, MapPin, Weight } from 'lucide-react'
import { type FormEvent, useEffect, useRef, useState } from 'react'

import {
  CHECKPOINT_INTERVALS,
  type CheckpointInterval,
  type Place,
  type PlannedTrip,
  type TripRequest,
} from '../api/types'
import { defaultDeparture, departureError, toLocalInputValue } from '../lib/departure'
import { MAX_LOAD_LB, parseLoad } from '../lib/load'
import { rememberPlaces } from '../lib/recentPlaces'
import surface from '../styles/surface.module.css'
import styles from './Form.module.css'
import { PlaceField } from './PlaceField'

interface TripFormProps {
  isPlanning: boolean
  onSubmit: (trip: PlannedTrip) => void
}

interface FormErrors {
  origin: string | null
  destination: string | null
  departure: string | null
  load: string | null
}

const loadFormat = new Intl.NumberFormat()

interface FormState {
  origin: Place | null
  destination: Place | null
  departure: string
  load: string
  interval: CheckpointInterval
  restBreaks: boolean
}

function validate(state: FormState): { errors: FormErrors; trip: TripRequest | null } {
  const { origin, destination, departure } = state
  const loadLb = parseLoad(state.load)
  const sameLocation =
    origin !== null &&
    destination !== null &&
    origin.position.lat === destination.position.lat &&
    origin.position.lon === destination.position.lon
  const errors: FormErrors = {
    origin: origin ? null : 'Choose an origin from the suggestions.',
    destination: !destination
      ? 'Choose a destination from the suggestions.'
      : sameLocation
        ? 'Destination must differ from the origin.'
        : null,
    departure: departureError(departure, new Date()),
    load:
      loadLb === null ? `Enter a load between 1 and ${loadFormat.format(MAX_LOAD_LB)} lb.` : null,
  }
  const trip =
    origin && destination && loadLb !== null && !errors.destination && !errors.departure
      ? {
          origin: origin.position,
          destination: destination.position,
          departure: new Date(departure).toISOString(),
          load_lb: loadLb,
          interval_mi: state.interval,
          rest_breaks: state.restBreaks,
        }
      : null
  return { errors, trip }
}

function FieldError({ message }: { message: string | null }) {
  return message && <p className={styles.error}>{message}</p>
}

export function TripForm({ isPlanning, onSubmit }: TripFormProps) {
  const [origin, setOrigin] = useState<Place | null>(null)
  const [destination, setDestination] = useState<Place | null>(null)
  const [departure, setDeparture] = useState(() => toLocalInputValue(defaultDeparture(new Date())))
  const [load, setLoad] = useState('')
  const [interval, setCheckpointInterval] = useState<CheckpointInterval>(25)
  const [restBreaks, setRestBreaks] = useState(true)
  const [attempted, setAttempted] = useState(false)
  const [focusRequest, setFocusRequest] = useState(0)
  const formRef = useRef<HTMLFormElement>(null)

  const { errors, trip } = validate({
    origin,
    destination,
    departure,
    load,
    interval,
    restBreaks,
  })
  const shown = (error: string | null) => (attempted ? error : null)

  useEffect(() => {
    if (focusRequest === 0) return
    const invalid = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]')
    invalid?.scrollIntoView({ block: 'center' })
    invalid?.focus({ preventScroll: true })
  }, [focusRequest])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setAttempted(true)
    if (trip && origin && destination) {
      rememberPlaces([origin, destination])
      onSubmit({ request: trip, origin, destination })
    } else {
      setFocusRequest((count) => count + 1)
    }
  }

  function swapPlaces() {
    setOrigin(destination)
    setDestination(origin)
  }

  function formatLoad() {
    const loadLb = parseLoad(load)
    if (loadLb !== null) setLoad(loadFormat.format(loadLb))
  }

  return (
    <form
      ref={formRef}
      className={`${surface.card} ${surface.rise} ${styles.form}`}
      onSubmit={handleSubmit}
      noValidate
    >
      <div className={styles.places}>
        <div className={styles.placeFields}>
          <PlaceField
            label="Origin"
            icon={MapPin}
            tone="origin"
            placeholder="City, address or facility"
            value={origin}
            onChange={setOrigin}
            error={shown(errors.origin)}
          />
          <PlaceField
            label="Destination"
            icon={Flag}
            tone="destination"
            placeholder="City, address or facility"
            value={destination}
            onChange={setDestination}
            error={shown(errors.destination)}
          />
        </div>
        <button
          type="button"
          className={styles.swap}
          onClick={swapPlaces}
          disabled={!origin && !destination}
          aria-label="Swap origin and destination"
          title="Swap origin and destination"
        >
          <ArrowUpDown />
        </button>
      </div>
      <div className={styles.row}>
        <Field className={styles.field}>
          <Label className={styles.label}>Departure</Label>
          <div className={styles.control}>
            <input
              className={styles.input}
              type="datetime-local"
              value={departure}
              onChange={(event) => setDeparture(event.target.value)}
              aria-invalid={shown(errors.departure) !== null}
            />
          </div>
          <FieldError message={shown(errors.departure)} />
        </Field>
        <Field className={styles.field}>
          <Label className={styles.label}>Load weight</Label>
          <div className={styles.control}>
            <Weight className={styles.icon} aria-hidden="true" />
            <input
              className={styles.input}
              inputMode="numeric"
              placeholder="42,000"
              value={load}
              onChange={(event) => setLoad(event.target.value)}
              onBlur={formatLoad}
              aria-invalid={shown(errors.load) !== null}
            />
            <span className={styles.suffix} aria-hidden="true">
              lb
            </span>
          </div>
          <FieldError message={shown(errors.load)} />
        </Field>
      </div>
      <RadioGroup
        value={interval}
        onChange={setCheckpointInterval}
        className={styles.field}
        aria-label="Weather checkpoint interval"
      >
        <span className={styles.label}>Weather checkpoint every</span>
        <div
          className={styles.segmented}
          style={{ '--selected': CHECKPOINT_INTERVALS.indexOf(interval) }}
        >
          <span className={styles.thumb} aria-hidden="true" />
          {CHECKPOINT_INTERVALS.map((miles) => (
            <Radio key={miles} value={miles} className={styles.segment}>
              {miles} mi
            </Radio>
          ))}
        </div>
      </RadioGroup>
      <Field className={styles.switchField}>
        <Label className={styles.switchLabel}>
          Hours-of-service stops
          <span className={styles.hint}>30 min break after 8 h, 10 h rest after 11 h</span>
        </Label>
        <Switch checked={restBreaks} onChange={setRestBreaks} className={styles.switch}>
          <span className={styles.knob} />
        </Switch>
      </Field>
      <button className={styles.submit} type="submit" disabled={isPlanning}>
        {isPlanning ? (
          <>
            <span className={surface.spinner} aria-hidden="true" />
            Planning routes…
          </>
        ) : (
          'Plan routes'
        )}
      </button>
    </form>
  )
}
