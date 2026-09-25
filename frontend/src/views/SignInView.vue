<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<'signin' | 'register'>('signin')
const email = ref('')
const password = ref('')
const displayName = ref('')
const busy = ref(false)
const error = ref<string | null>(null)

const isRegister = computed(() => mode.value === 'register')

function switchTo(next: 'signin' | 'register'): void {
  mode.value = next
  error.value = null
}

async function submit(): Promise<void> {
  if (!email.value.trim() || !password.value) {
    error.value = 'Enter your email and password.'
    return
  }
  if (isRegister.value && password.value.length < 10) {
    error.value = 'Passwords need at least 10 characters.'
    return
  }

  busy.value = true
  error.value = null
  try {
    if (isRegister.value) {
      await auth.register(
        email.value.trim(),
        password.value,
        displayName.value.trim() || email.value.split('@')[0]
      )
    } else {
      await auth.login(email.value.trim(), password.value)
    }
    // Back to wherever the guard interrupted, or the checklist.
    const next = typeof route.query.next === 'string' ? route.query.next : '/'
    router.replace(next)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    busy.value = false
    password.value = ''
  }
}

onMounted(auth.loadConfig)
</script>

<template>
  <div class="signin">
    <header>
      <h1>BeautyAlarm</h1>
      <p class="muted">{{ isRegister ? 'Create your account.' : 'Sign in to your routines.' }}</p>
    </header>

    <div v-if="auth.allowRegistration" class="segmented" role="group" aria-label="Sign in or register">
      <button type="button" :aria-pressed="!isRegister" @click="switchTo('signin')">Sign in</button>
      <button type="button" :aria-pressed="isRegister" @click="switchTo('register')">Create account</button>
    </div>

    <p v-if="error" class="banner banner-error" role="alert">{{ error }}</p>

    <form @submit.prevent="submit">
      <label class="field">
        <span>Email</span>
        <input
          v-model="email"
          type="email"
          autocomplete="username"
          inputmode="email"
          autocapitalize="none"
          spellcheck="false"
          placeholder="you@example.com"
        />
      </label>

      <label v-if="isRegister" class="field">
        <span>Display name</span>
        <input v-model="displayName" autocomplete="nickname" placeholder="Your name" />
      </label>

      <label class="field">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
        />
        <small v-if="isRegister" class="hint">At least 10 characters. Length beats punctuation.</small>
      </label>

      <button class="btn btn-primary block" type="submit" :disabled="busy">
        {{ busy ? 'Just a moment…' : isRegister ? 'Create account' : 'Sign in' }}
      </button>
    </form>

    <p class="muted footnote">
      Everyone in the house gets their own account. Your routines and history are
      yours alone.
    </p>
  </div>
</template>

<style scoped>
.signin {
  max-width: 24rem;
  margin: 0 auto;
  padding: 3rem 0 1rem;
}

header { margin-bottom: 1.5rem; }
header h1 { margin-bottom: 0.25rem; }
header p { margin: 0; }

.segmented { margin-bottom: 1.25rem; }

.block { width: 100%; margin-top: 0.5rem; }

.footnote {
  margin-top: 2rem;
  font-size: 0.8125rem;
  text-align: center;
  text-wrap: pretty;
}
</style>
