<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="app" :class="{ 'no-nav': !auth.signedIn }">
    <RouterView />
  </div>
  <!-- No tab bar on the sign-in screen: there is nowhere to go yet, and the
       bottom padding it reserves would leave a gap under a short form. -->
  <nav v-if="auth.signedIn" class="nav">
    <RouterLink to="/">Today</RouterLink>
    <RouterLink to="/routines">Routines</RouterLink>
    <RouterLink to="/progress">Progress</RouterLink>
    <RouterLink to="/settings">Settings</RouterLink>
  </nav>
</template>
