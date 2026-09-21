export type TimePeriod = 'morning' | 'night'
export type LogStatus = 'completed' | 'skipped'

export interface Product {
  id: number
  name: string
  brand: string | null
  notes: string | null
  archived_at: string | null
}

export interface Routine {
  id: number
  product_id: number
  /** ISO weekdays, 1 = Monday .. 7 = Sunday (D2). */
  days_of_week: number[]
  time_period: TimePeriod
  /** Local wall clock, "HH:MM:SS", or null for no notification. */
  notification_time: string | null
  is_active: boolean
  end_date: string | null
  product: Product | null
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

export interface TodayResponse {
  date: string
  entries: TodayEntry[]
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
  product_id: number
  days_of_week: number[]
  time_period: TimePeriod
  notification_time: string | null
  is_active: boolean
  end_date: string | null
}

export interface RoutineAdherence {
  routine_id: number
  product_name: string
  due: number
  completed: number
}
