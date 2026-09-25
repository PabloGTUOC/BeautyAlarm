import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from './stores/auth'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'today', component: () => import('./views/TodayView.vue') },
    { path: '/routines', name: 'routines', component: () => import('./views/RoutinesView.vue') },
    {
      path: '/routines/new',
      name: 'routine-new',
      component: () => import('./views/RoutineEditView.vue')
    },
    {
      path: '/routines/:id',
      name: 'routine-edit',
      component: () => import('./views/RoutineEditView.vue'),
      props: true
    },
    { path: '/progress', name: 'progress', component: () => import('./views/ProgressView.vue') },
    { path: '/settings', name: 'settings', component: () => import('./views/SettingsView.vue') },
    {
      path: '/signin',
      name: 'signin',
      component: () => import('./views/SignInView.vue'),
      meta: { public: true }
    },
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  // Resolve once per load: the session is an httpOnly cookie, so the only way
  // to know whether we are signed in is to ask the server.
  await auth.resolve()

  if (to.meta.public) {
    return auth.signedIn ? { name: 'today' } : true
  }
  if (!auth.signedIn) {
    // Remember where they were headed so sign-in can finish the journey.
    return { name: 'signin', query: to.fullPath === '/' ? {} : { next: to.fullPath } }
  }
  return true
})
