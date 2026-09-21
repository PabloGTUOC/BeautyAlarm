import { api } from './api'

/** Web Push needs all three; iOS only provides them once installed to the home screen. */
export function pushSupported(): boolean {
  return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
}

/** VAPID keys travel as base64url; PushManager wants raw bytes. */
export function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=')
  const binary = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

async function registration(): Promise<ServiceWorkerRegistration> {
  const existing = await navigator.serviceWorker.getRegistration()
  if (existing) return existing
  return navigator.serviceWorker.ready
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null
  const registered = await navigator.serviceWorker.getRegistration()
  return registered ? registered.pushManager.getSubscription() : null
}

/** Ask for permission, subscribe, and register with the API. Must run from a user gesture. */
export async function enablePush(): Promise<void> {
  if (!pushSupported()) {
    throw new Error('This browser cannot receive push notifications. On iOS, add the app to your home screen first.')
  }
  const permission = await Notification.requestPermission()
  if (permission !== 'granted') {
    throw new Error('Notification permission was not granted.')
  }

  const { public_key: publicKey } = await api.pushPublicKey()
  const reg = await registration()
  const subscription =
    (await reg.pushManager.getSubscription()) ??
    (await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey)
    }))

  await api.pushSubscribe(subscription.toJSON() as PushSubscriptionJSON)
}

export async function disablePush(): Promise<void> {
  const subscription = await currentSubscription()
  if (!subscription) return
  await api.pushUnsubscribe(subscription.endpoint)
  await subscription.unsubscribe()
}
