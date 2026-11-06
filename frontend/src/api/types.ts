export const RISK_LEVELS = [0, 1, 2, 3, 4] as const
export type RiskLevel = (typeof RISK_LEVELS)[number]

export const CHECKPOINT_INTERVALS = [10, 25, 50] as const
export type CheckpointInterval = (typeof CHECKPOINT_INTERVALS)[number]

export interface Position {
  lat: number
  lon: number
}

export interface Place {
  label: string
  position: Position
}

export interface TripRequest {
  origin: Position
  destination: Position
  departure: string
  load_lb: number
  interval_mi: CheckpointInterval
  rest_breaks: boolean
}

export interface Conditions {
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
}

export interface Assessment {
  level: RiskLevel
  wind: RiskLevel
  rain: RiskLevel
  snow: RiskLevel
  load_adjusted: boolean
}

export interface Checkpoint {
  mile: number
  position: Position
  eta: string
  conditions: Conditions
  risk: Assessment
}

export interface Segment {
  level: RiskLevel
  start_mile: number
  end_mile: number
  coordinates: [number, number][]
}

export interface Stop {
  kind: 'break' | 'rest'
  mile: number
  position: Position
  start: string
  end: string
}

export interface RouteSummary {
  low_mi: number
  moderate_mi: number
  high_mi: number
  severe_mi: number
  no_travel_mi: number
  average_risk: number
}

export interface Route {
  distance_mi: number
  driving_s: number
  duration_s: number
  departure: string
  arrival: string
  summary: RouteSummary
  checkpoints: Checkpoint[]
  segments: Segment[]
  stops: Stop[]
}

export type DecidingFactor =
  | 'only_route'
  | 'no_travel_miles'
  | 'severe_miles'
  | 'high_miles'
  | 'average_risk'
  | 'travel_time'
  | 'tie'

export interface Recommendation {
  index: number
  deciding_factor: DecidingFactor
  runner_up_index: number | null
}

export interface Heatmap {
  cell_deg: number
  cells: Position[]
  hours: string[]
  risk: RiskLevel[][]
  wind_mph: number[][]
  rain_in_hr: number[][]
  snow_in_hr: number[][]
}

export interface VerificationCheck {
  key: string
  title: string
  passed: boolean
  detail: string
}

export interface Verification {
  passed: boolean
  checks: VerificationCheck[]
}

export interface TripPlan {
  routes: Route[]
  recommendation: Recommendation
  heatmap: Heatmap
  verification: Verification
}

export interface PlannedTrip {
  request: TripRequest
  origin: Place
  destination: Place
}
