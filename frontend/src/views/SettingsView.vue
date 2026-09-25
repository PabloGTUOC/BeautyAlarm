<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import { useRouter } from 'vue-router'
import { currentSubscription, disablePush, enablePush, pushSupported } from '../push'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const signingOut = ref(false)
const supported = ref(false)
const subscribed = ref(false)
const working = ref(false)
const message = ref<string | null>(null)
const error = ref<string | null>(null)

async function signOut(): Promise<void> {
  signingOut.value = true
  try {
    await auth.logout()
    router.replace({ name: 'signin' })
  } finally {
    signingOut.value = false
  }
}

async function refreshSubscription(): Promise<void> {
  subscribed.value = (await currentSubscription()) !== null
}

async function toggle(): Promise<void> {
  working.value = true
  error.value = null
  message.value = null
  try {
    if (subscribed.value) {
      await disablePush()
      message.value = 'Notifications turned off.'
    } else {
      await enablePush()
      message.value = 'Notifications turned on.'
    }
    await refreshSubscription()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    working.value = false
  }
}

async function sendTest(): Promise<void> {
  working.value = true
  error.value = null
  message.value = null
  try {
    const { delivered } = await api.pushTest()
    message.value = delivered
      ? `Sent to ${delivered} device${delivered === 1 ? '' : 's'}.`
      : 'No devices are subscribed yet.'
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    working.value = false
  }
}

onMounted(async () => {
  supported.value = pushSupported()
  if (supported.value) await refreshSubscription()
})
</script>

<template>
  <header class="app-header">
    <h1>Settings</h1>
  </header>

  <p v-if="error" class="banner banner-error">{{ error }}</p>
  <p v-if="message" class="banner banner-info">{{ message }}</p>

  <div class="card">
    <h2 style="margin-top: 0">Account</h2>
    <p class="who">{{ auth.user?.display_name }}</p>
    <p class="muted">{{ auth.user?.email }}</p>
    <div class="actions">
      <button class="btn" :disabled="signingOut" @click="signOut">
        {{ signingOut ? 'Signing out…' : 'Sign out' }}
      </button>
    </div>
  </div>

  <div class="card">
    <h2 style="margin-top: 0">Notifications</h2>
    <p v-if="!supported" class="muted">
      This browser cannot receive push notifications. On iOS, add BeautyAlarm to your
      home screen first, then reopen it from there.
    </p>
    <template v-else>
      <p class="muted">
        {{ subscribed ? 'This device is subscribed.' : 'This device is not subscribed.' }}
        Reminders for your routines only, never anyone else's.
      </p>
      <div class="actions">
        <button class="btn btn-primary" :disabled="working" @click="toggle">
          {{ subscribed ? 'Turn off' : 'Turn on' }}
        </button>
        <button class="btn" :disabled="working || !subscribed" @click="sendTest">
          Send test
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.who { margin: 0; font-size: 1.0625rem; font-weight: 600; }
.card .muted { margin: 0.15rem 0 0; }
.card .actions { margin-top: 0.875rem; }
</style>
