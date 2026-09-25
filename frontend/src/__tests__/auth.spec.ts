import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// vi.mock is hoisted above every top-level declaration, so the mock's contents
// have to be hoisted with it rather than merely declared above the call.
const { api, ApiError } = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(public status: number, message: string) {
      super(message)
    }
  }
  return {
    ApiError,
    api: {
      me: vi.fn(),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
      authConfig: vi.fn()
    }
  }
})

vi.mock('../api', () => ({ ApiError, api }))

import { useAuthStore } from '../stores/auth'

const user = { id: 1, email: 'a@b.com', display_name: 'A' }

beforeEach(() => {
  setActivePinia(createPinia())
  Object.values(api).forEach((fn) => fn.mockReset())
  api.authConfig.mockResolvedValue({ allow_registration: true })
})

describe('auth store', () => {
  it('starts unresolved so the guard can wait instead of bouncing', () => {
    const auth = useAuthStore()
    expect(auth.resolved).toBe(false)
    expect(auth.signedIn).toBe(false)
  })

  it('resolves the session from the server, since the cookie is unreadable', async () => {
    api.me.mockResolvedValue(user)
    const auth = useAuthStore()
    await auth.resolve()
    expect(auth.signedIn).toBe(true)
    expect(auth.user?.display_name).toBe('A')
  })

  it('treats a 401 as signed out rather than an error', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    api.me.mockRejectedValue(new ApiError(401, 'Not signed in'))
    const auth = useAuthStore()
    await auth.resolve()
    expect(auth.signedIn).toBe(false)
    expect(auth.resolved).toBe(true)
    expect(warn).not.toHaveBeenCalled()
    warn.mockRestore()
  })

  it('only resolves once, so every navigation is not a round trip', async () => {
    api.me.mockResolvedValue(user)
    const auth = useAuthStore()
    await auth.resolve()
    await auth.resolve()
    expect(api.me).toHaveBeenCalledTimes(1)
  })

  it('clears the user even when the logout request fails', async () => {
    api.me.mockResolvedValue(user)
    api.logout.mockRejectedValue(new Error('network down'))
    const auth = useAuthStore()
    await auth.resolve()
    expect(auth.signedIn).toBe(true)

    await expect(auth.logout()).rejects.toThrow('network down')
    // Staying "signed in" after a logout attempt would be a lie.
    expect(auth.signedIn).toBe(false)
  })

  it('signs in and remembers who it is', async () => {
    api.login.mockResolvedValue(user)
    const auth = useAuthStore()
    await auth.login('a@b.com', 'correct-horse-battery')
    expect(auth.signedIn).toBe(true)
    expect(auth.resolved).toBe(true)
  })

  it('offers sign-up when the server cannot be asked', async () => {
    api.authConfig.mockRejectedValue(new Error('offline'))
    const auth = useAuthStore()
    await auth.loadConfig()
    // The server rejects registration anyway when it is off, so defaulting to
    // showing the tab is the harmless direction to fail in.
    expect(auth.allowRegistration).toBe(true)
  })

  it('hides sign-up when registration is closed', async () => {
    api.authConfig.mockResolvedValue({ allow_registration: false })
    const auth = useAuthStore()
    await auth.loadConfig()
    expect(auth.allowRegistration).toBe(false)
  })
})
