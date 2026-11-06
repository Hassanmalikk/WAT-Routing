import type { Checkpoint, RiskLevel } from '../api/types'
import { formatDateTime } from '../lib/format'
import { RISK_COLORS, RISK_LABELS } from '../lib/risk'
import styles from './Map.module.css'

function LevelTag({ level }: { level: RiskLevel }) {
  return (
    <span className={styles.levelTag} style={{ '--risk': RISK_COLORS[level] }}>
      {RISK_LABELS[level]}
    </span>
  )
}

export function CheckpointDetails({ checkpoint }: { checkpoint: Checkpoint }) {
  const { conditions, risk } = checkpoint
  return (
    <div className={styles.details}>
      <div className={styles.detailsHeader}>
        <strong>Mile {Math.round(checkpoint.mile)}</strong>
        <LevelTag level={risk.level} />
      </div>
      <p className={styles.detailsEta}>ETA {formatDateTime(checkpoint.eta)}</p>
      <dl className={styles.conditions}>
        <dt>Wind</dt>
        <dd>
          {conditions.wind_mph.toFixed(0)} mph
          <span className={styles.muted}> · gusts {conditions.gust_mph.toFixed(0)}</span>
        </dd>
        <dd>
          <LevelTag level={risk.wind} />
        </dd>
        <dt>Rain</dt>
        <dd>{conditions.rain_in_hr.toFixed(2)} in/hr</dd>
        <dd>
          <LevelTag level={risk.rain} />
        </dd>
        <dt>Snow</dt>
        <dd>{conditions.snow_in_hr.toFixed(2)} in/hr</dd>
        <dd>
          <LevelTag level={risk.snow} />
        </dd>
      </dl>
      {risk.load_adjusted && (
        <p className={styles.note}>Wind risk raised one level for this load weight.</p>
      )}
    </div>
  )
}
