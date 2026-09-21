import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TodayRow from '../components/TodayRow.vue'
import type { TodayEntry } from '../types'

function entry(overrides: Partial<TodayEntry> = {}): TodayEntry {
  return {
    routine: {
      id: 1,
      product_id: 1,
      days_of_week: [1],
      time_period: 'night',
      notification_time: '22:00:00',
      is_active: true,
      end_date: null,
      product: { id: 1, name: 'Retinol', brand: 'CeraVe', notes: null, archived_at: null }
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

  it('shows the product, brand and notification time', () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: false } })
    expect(wrapper.text()).toContain('Retinol')
    expect(wrapper.text()).toContain('CeraVe · 22:00')
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
    expect(wrapper.text()).toContain('Done')
    expect(wrapper.find('.strike').exists()).toBe(true)

    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('undo')).toHaveLength(1)
  })

  it('disables its buttons while busy', () => {
    const wrapper = mount(TodayRow, { props: { entry: entry(), busy: true } })
    expect(wrapper.findAll('button').every((b) => b.attributes('disabled') !== undefined)).toBe(true)
  })
})
