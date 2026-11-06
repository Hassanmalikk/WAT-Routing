import { CircleCheck, CircleX } from 'lucide-react'

import type { Verification } from '../api/types'
import styles from './Summary.module.css'

export function VerificationList({ verification }: { verification: Verification }) {
  return (
    <div className={styles.checks}>
      <p className={styles.checksIntro}>
        A separate checker re-derives every number from the finished plan, without using the
        planner’s code, and confirms it follows the rules.
      </p>
      <ul>
        {verification.checks.map((check) => (
          <li key={check.key} data-passed={check.passed}>
            {check.passed ? <CircleCheck aria-label="Passed" /> : <CircleX aria-label="Failed" />}
            <span>
              <strong>{check.title}</strong>
              <span>{check.detail}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
