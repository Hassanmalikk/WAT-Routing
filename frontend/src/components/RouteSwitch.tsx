import { Radio, RadioGroup } from '@headlessui/react'

import { routeLetter, routeName } from '../lib/routes'
import styles from './Summary.module.css'

interface RouteSwitchProps {
  count: number
  selectedIndex: number
  recommendedIndex: number
  onSelect: (index: number) => void
}

export function RouteSwitch({
  count,
  selectedIndex,
  recommendedIndex,
  onSelect,
}: RouteSwitchProps) {
  if (count < 2) return null
  return (
    <RadioGroup
      value={selectedIndex}
      onChange={onSelect}
      className={styles.routeSwitch}
      aria-label="Route"
    >
      {Array.from({ length: count }, (_, index) => (
        <Radio
          key={index}
          value={index}
          className={styles.routeOption}
          aria-label={routeName(index)}
        >
          {routeLetter(index)}
          {index === recommendedIndex && <span className={styles.safest}>Safest</span>}
        </Radio>
      ))}
    </RadioGroup>
  )
}
