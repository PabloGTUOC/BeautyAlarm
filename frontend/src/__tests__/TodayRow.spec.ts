import { mount } from '@vue/test-utils'

const read = (w: { text: () => string }) => w.text().replace(/\s+/g, ' ').trim()
import { describe, expect, it } from 'vitest'
import TodayRow from '../components/TodayRow.vue'
import type { TodayEntry } from '../types'

function entry(overrides: Partial<TodayEntry> = {}): TodayEntry {
  return {
    routine: {
      id: 1,
      name: 'Retinol',
      kind: 'scheduled',
      days_of_week: [1],
      time_period: 'night',
      target_interval_days: null,
      start_date: null,
      notification_time: '22:00:00',
      is_active: true,
      end_date: null,
      products: [
        { id: 1, name: 'Retinol', brand: 'CeraVe', notes: null, archived_at: null }
      ]
    },
    log: null,
    ...overrides
  }
}

describe('TodayRow', () => {
  it('offers Done and Skip while pending', () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: false } })
    const labels = wrapper.findAll('button').map((b) => b.text())
    expect(labels).toEqual(['Skip', 'Done'])
  })

  it('shows the routine name, brand and notification time', () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: false } })
    expect(read(wrapper)).toContain('Retinol')
    expect(read(wrapper)).toContain('CeraVe')
    expect(read(wrapper)).toContain('22:00')
  })

  it('lists several products in application order (D8a)', () => {
    const layered = entry()
    layered.routine.name = 'Night stack'
    layered.routine.products = [
      { id: 1, name: 'Hyaluronic Acid', brand: null, notes: null, archived_at: null },
      { id: 2, name: 'Peptides', brand: null, notes: null, archived_at: null },
      { id: 3, name: 'Moisturizer', brand: null, notes: null, archived_at: null }
    ]
    const wrapper = mount(TodayRow, { props: { entry: layered, busy: false } })
    expect(read(wrapper)).toContain('Night stack')
    expect(read(wrapper)).toContain('Hyaluronic Acid → Peptides → Moisturizer')
  })

  it('still offers one tick for a multi-product routine (D6)', () => {
    const layered = entry()
    layered.routine.products = [
      { id: 1, name: 'A', brand: null, notes: null, archived_at: null },
      { id: 2, name: 'B', brand: null, notes: null, archived_at: null }
    ]
    const wrapper = mount(TodayRow, { props: { entry: layered, busy: false } })
    expect(wrapper.findAll('button').map((b) => b.text())).toEqual(['Skip', 'Done'])
  })

  it('renders a routine with no products, such as a service', () => {
    const service = entry()
    service.routine.name = 'Facial'
    service.routine.products = []
    const wrapper = mount(TodayRow, { props: { entry: service, busy: false } })
    expect(read(wrapper)).toContain('Facial')
  })

  it('emits the status that was clicked', async () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: false } })
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('log')).toEqual([['completed']])
  })

  it('switches to an undo affordance once logged', async () => {
    const logged = entry({
      log: { id: 9, routine_id: 1, log_date: '2026-09-21', timestamp: '', status: 'completed' }
    })
    const wrapper = mount(TodayRow, { props: { entry: logged, busy: false } })
    expect(read(wrapper)).toContain('Done')
    expect(wrapper.find('.strike').exists()).toBe(true)

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('undo')).toHaveLength(1)
  })

  it('disables its buttons while busy', () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: true } })
    expect(wrapper.findAll('button').every((b) => b.attributes('disabled') !== undefined)).toBe(true)
  })
})
