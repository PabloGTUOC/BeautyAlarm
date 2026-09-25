import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { Product, Routine, TodayEntry, TodayResponse } from '../types'

const today = '2026-09-25'

const api = {
  today: vi.fn<() => Promise<TodayResponse>>(),
  streak: vi.fn(),
  listRoutines: vi.fn(),
  logRoutine: vi.fn(),
  deleteLog: vi.fn()
}
vi.mock('../api', () => ({ api: new Proxy({}, { get: (_t, k: string) => api[k as keyof typeof api] }) }))

import TodayView from '../views/TodayView.vue'

const product = (id: number, name: string): Product => ({
  id, name, brand: null, notes: null, archived_at: null
})

const routine = (id: number, name: string, over: Partial<Routine> = {}): Routine => ({
  id,
  name,
  kind: 'scheduled',
  days_of_week: [1, 2, 3, 4, 5, 6, 7],
  time_period: 'morning',
  target_interval_days: null,
  start_date: null,
  notification_time: null,
  is_active: true,
  end_date: null,
  products: [product(id, 'Something')],
  ...over
})

const entry = (id: number, name: string, status: 'completed' | 'skipped' | null): TodayEntry => ({
  routine: routine(id, name),
  log: status ? { id, routine_id: id, log_date: today, timestamp: '', status } : null
})

const respond = (over: Partial<TodayResponse> = {}): TodayResponse => ({
  date: today, entries: [], tracking: [], ...over
})

/** Text with element boundaries collapsed, so assertions read as a user would. */
const read = (w: { text: () => string }) => w.text().replace(/\s+/g, ' ').trim()

async function render() {
  const wrapper = mount(TodayView, { global: { stubs: { RouterLink: { template: '<a><slot/></a>' } } } })
  await flushPromises()
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  Object.values(api).forEach((fn) => fn.mockReset())
  api.streak.mockResolvedValue({ current: 6, longest: 23 })
  api.listRoutines.mockResolvedValue([])
})

describe('TodayView completion state', () => {
  it('acknowledges the day once every routine is completed, with the streak', async () => {
    api.today.mockResolvedValue(respond({ entries: [entry(1, 'Cleanse', 'completed')] }))
    const wrapper = await render()
    expect(read(wrapper)).toContain('All done for today.')
    expect(read(wrapper)).toContain('6 days in a row.')
  })

  it('does not celebrate a day that was partly skipped', async () => {
    api.today.mockResolvedValue(
      respond({ entries: [entry(1, 'Cleanse', 'completed'), entry(2, 'Retinol', 'skipped')] })
    )
    const wrapper = await render()
    expect(read(wrapper)).toContain('Nothing left for today.')
    expect(read(wrapper)).toContain('1 done, 1 skipped.')
    expect(read(wrapper)).not.toContain('All done')
    expect(api.streak).not.toHaveBeenCalled()
  })

  it('stays quiet while anything is still pending', async () => {
    api.today.mockResolvedValue(
      respond({ entries: [entry(1, 'Cleanse', 'completed'), entry(2, 'Retinol', null)] })
    )
    const wrapper = await render()
    expect(read(wrapper)).not.toContain('All done for today.')
    expect(read(wrapper)).toContain('1/2')
  })
})

describe('TodayView empty states', () => {
  it('offers a way in when no routines exist at all', async () => {
    api.today.mockResolvedValue(respond())
    api.listRoutines.mockResolvedValue([])
    const wrapper = await render()
    expect(read(wrapper)).toContain('No routines yet.')
    expect(read(wrapper)).toContain('Add a routine')
  })

  it('does not tell someone with routines to add one on a rest day', async () => {
    api.today.mockResolvedValue(respond())
    api.listRoutines.mockResolvedValue([routine(9, 'Weekend mask', { days_of_week: [6] })])
    const wrapper = await render()
    expect(read(wrapper)).toContain('Nothing due today.')
    expect(read(wrapper)).toContain('A rest day.')
    expect(read(wrapper)).not.toContain('Add a routine')
  })
})

describe('TodayView error state', () => {
  it('explains the failure in plain words and offers a retry', async () => {
    api.today.mockRejectedValueOnce(new Error('Internal Server Error'))
    const wrapper = await render()
    expect(read(wrapper)).toContain('Could not reach the server.')
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)

    // Retrying re-runs the load and recovers.
    api.today.mockResolvedValue(respond({ entries: [entry(1, 'Cleanse', null)] }))
    await wrapper.find('[role="alert"] button').trigger('click')
    await flushPromises()
    await flushPromises()
    expect(read(wrapper)).not.toContain('Could not reach the server.')
    expect(read(wrapper)).toContain('Cleanse')
  })

  it('keeps the date visible when the load fails', async () => {
    api.today.mockRejectedValue(new Error('boom'))
    const wrapper = await render()
    expect(wrapper.find('.subtitle').text()).not.toBe('')
  })
})
