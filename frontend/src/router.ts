import { createRouter, createWebHistory } from 'vue-router'

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
    { path: '/:pathMatch(.*)*', redirect: '/' }
  ]
})
