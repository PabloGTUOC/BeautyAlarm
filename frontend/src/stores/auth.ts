import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError, api } from '../api'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  /** Null until the first /auth/me has settled, so the guard can wait rather
   *  than bouncing a signed-in person to the login screen on a hard refresh. */
  const resolved = ref(false)
  const allowRegistration = ref(true)

  const signedIn = computed(() => user.value !== null)

  /** Ask the server who we are. The session is an httpOnly cookie, so this is
   *  the only way to find out; there is nothing readable on the client. */
  async function resolve(): Promise<void> {
    if (resolved.value) return
    try {
      user.value = await api.me()
    } catch (err) {
      // 401 is the normal "not signed in" answer, not a failure worth showing.
      if (!(err instanceof ApiError && err.status === 401)) {
        console.warn('auth: could not resolve session', err)
      }
      user.value = null
    } finally {
      resolved.value = true
    }
  }

  async function loadConfig(): Promise<void> {
    try {
      allowRegistration.value = (await api.authConfig()).allow_registration
    } catch {
      // If we cannot tell, offer sign-up: the server rejects it anyway when off.
      allowRegistration.value = true
    }
  }

  async function login(email: string, password: string): Promise<void> {
    user.value = await api.login({ email, password })
    resolved.value = true
  }

  async function register(
    email: string,
    password: string,
    displayName: string
  ): Promise<void> {
    user.value = await api.register({ email, password, display_name: displayName })
    resolved.value = true
  }

  async function logout(): Promise<void> {
    try {
      await api.logout()
    } finally {
      // Local state clears even if the request failed; the cookie is gone or
      // the session is dead either way, and staying "signed in" would be a lie.
      user.value = null
    }
  }

  /** Called by the API layer when any request 401s: the session expired
   *  underneath us, so the app should fall back to the login screen. */
  function forget(): void {
    user.value = null
    resolved.value = true
  }

  return {
    user, resolved, allowRegistration, signedIn,
    resolve, loadConfig, login, register, logout, forget
  }
})
