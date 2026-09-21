<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, getToken, setToken } from '../api'
import { currentSubscription, disablePush, enablePush, pushSupported } from '../push'

const token = ref('')
const tokenSaved = ref(false)
const supported = ref(false)
const subscribed = ref(false)
const working = ref(false)
const message = ref<string | null>(null)
const error = ref<string | null>(null)

function saveToken(): void {
  setToken(token.value.trim())
  tokenSaved.value = true
  setTimeout(() => (tokenSaved.value = false), 2000)
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
  token.value = getToken()
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
    <h2 style="margin-top: 0">API token</h2>
    <p class="muted">
      Stored in this browser only and sent with every request. Leave empty if the
      server runs without a token.
    </p>
    <label class="field">
      <input v-model="token" type="password" autocomplete="off" placeholder="API_TOKEN" />
    </label>
    <button class="btn btn-primary" @click="saveToken">
      {{ tokenSaved ? 'Saved' : 'Save token' }}
    </button>
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
