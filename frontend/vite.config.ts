import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['icon-192.png', 'icon-512.png'],
      manifest: {
        name: 'BeautyAlarm',
        short_name: 'BeautyAlarm',
        description: 'Track your beauty and skincare routines.',
        theme_color: '#b5476d',
        background_color: '#fdf7f9',
        display: 'standalone',
        start_url: '/',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' }
        ]
      },
      workbox: {
        // The push and notificationclick handlers live in a plain script so the
        // generated service worker stays generated (specs.md section 7).
        importScripts: ['push-sw.js'],
        // The API is never precached: a stale checklist is worse than no checklist.
        navigateFallbackDenylist: [/^\/api\//]
      }
    })
  ],
  // `vite preview` serves the production build; giving it the same proxy makes
  // it behave like nginx does in front of the real deployment (D9).
  preview: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  server: {
    proxy: {
      // Mirrors what nginx does in production (D9), so the app is same-origin
      // in development too and never needs CORS.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true
  }
})
