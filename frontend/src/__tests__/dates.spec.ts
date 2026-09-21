import { describe, expect, it } from 'vitest'
import {
  addDays,
  describeDays,
  fromLocalIsoDate,
  isoWeekday,
  toLocalIsoDate,
  trimSeconds
} from '../dates'

describe('isoWeekday', () => {
  it('maps Monday to 1 and Sunday to 7 (D2)', () => {
    expect(isoWeekday(new Date(2026, 8, 21))).toBe(1) // Monday
    expect(isoWeekday(new Date(2026, 8, 27))).toBe(7) // Sunday
  })

  it('never returns 0, which is what getDay() would give for Sunday', () => {
    for (let day = 21; day <= 27; day += 1) {
      const iso = isoWeekday(new Date(2026, 8, day))
      expect(iso).toBeGreaterThanOrEqual(1)
      expect(iso).toBeLessThanOrEqual(7)
    }
  })
})

describe('toLocalIsoDate', () => {
  it('formats a local date', () => {
    expect(toLocalIsoDate(new Date(2026, 0, 5))).toBe('2026-01-05')
  })

  it('does not shift the day near midnight the way toISOString would', () => {
    // 00:30 local. In any timezone west of UTC, toISOString() reports the next day.
    const justAfterMidnight = new Date(2026, 8, 21, 0, 30)
    expect(toLocalIsoDate(justAfterMidnight)).toBe('2026-09-21')
  })

  it('round-trips through fromLocalIsoDate', () => {
    const original = new Date(2026, 11, 31)
    expect(toLocalIsoDate(fromLocalIsoDate(toLocalIsoDate(original)))).toBe('2026-12-31')
  })
})

describe('addDays', () => {
  it('crosses month boundaries', () => {
    expect(toLocalIsoDate(addDays(new Date(2026, 0, 31), 1))).toBe('2026-02-01')
  })

  it('goes backwards', () => {
    expect(toLocalIsoDate(addDays(new Date(2026, 0, 1), -1))).toBe('2025-12-31')
  })

  it('does not mutate its argument', () => {
    const original = new Date(2026, 0, 1)
    addDays(original, 5)
    expect(toLocalIsoDate(original)).toBe('2026-01-01')
  })
})

describe('describeDays', () => {
  it('names the common sets', () => {
    expect(describeDays([1, 2, 3, 4, 5, 6, 7])).toBe('Every day')
    expect(describeDays([1, 2, 3, 4, 5])).toBe('Weekdays')
    expect(describeDays([6, 7])).toBe('Weekends')
  })

  it('lists anything else in order', () => {
    expect(describeDays([5, 1, 3])).toBe('Mon, Wed, Fri')
  })
})

describe('trimSeconds', () => {
  it('drops seconds and tolerates null', () => {
    expect(trimSeconds('22:00:00')).toBe('22:00')
    expect(trimSeconds(null)).toBe('')
  })
})
