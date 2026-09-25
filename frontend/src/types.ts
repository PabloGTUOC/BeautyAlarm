export type TimePeriod = 'morning' | 'night'
export type LogStatus = 'completed' | 'skipped'
/** How a routine's due-ness is decided (D11). */
export type RoutineKind = 'scheduled' | 'tracked'
/** Where a tracked routine stands against its interval (D11). Three states,
 *  because the day the target is reached is the day to act, not the day you
 *  are already late. */
export type TrackerStatus = 'waiting' | 'due' | 'overdue'

export interface User {
  id: number
  email: string
  display_name: string
}

export interface AuthConfig {
  allow_registration: boolean
}

export interface Product {
  id: number
  name: string
  brand: string | null
  notes: string | null
  archived_at: string | null
}

export interface Routine {
  id: number
  /** Required: with 0 or 3 products there is no product name to borrow (D8a). */
  name: string
  kind: RoutineKind
  /** ISO weekdays, 1 = Monday .. 7 = Sunday (D2). Null when tracked. */
  days_of_week: number[] | null
  /** Null when tracked. */
  time_period: TimePeriod | null
  /** Days between occurrences. Set only when tracked. */
  target_interval_days: number | null
  /** Not due before this local date (G28). */
  start_date: string | null
  /** Local wall clock, "HH:MM:SS", or null for no notification. */
  notification_time: string | null
  is_active: boolean
  end_date: string | null
  /** In application order. Empty for an action or service (D8a). */
  products: Product[]
}

export interface DailyLog {
  id: number
  routine_id: number
  log_date: string
  timestamp: string
  status: LogStatus
}

export interface TodayEntry {
  routine: Routine
  /** Absent means pending (D6). */
  log: DailyLog | null
}

/** A tracked routine's elapsed-time state (D11). */
export interface TrackingEntry {
  routine: Routine
  last_completed: string | null
  /** Null when there is no baseline to measure from. */
  days_since: number | null
  status: TrackerStatus
}

export interface TodayResponse {
  date: string
  entries: TodayEntry[]
  /** Always present, not only when something is overdue. */
  tracking: TrackingEntry[]
}

export interface CalendarDay {
  date: string
  due: number
  completed: number
  skipped: number
}

export interface Streak {
  current: number
  longest: number
}

export interface RoutineInput {
  name: string
  kind: RoutineKind
  /** Ordered: index 0 is applied first (D8a). */
  product_ids: number[]
  days_of_week: number[] | null
  time_period: TimePeriod | null
  target_interval_days: number | null
  start_date: string | null
  notification_time: string | null
  is_active: boolean
  end_date: string | null
}

export interface RoutineAdherence {
  routine_id: number
  routine_name: string
  due: number
  completed: number
}
