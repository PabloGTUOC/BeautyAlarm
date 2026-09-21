<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app">
    <RouterView />
  </div>
  <nav class="nav">
    <RouterLink to="/">Today</RouterLink>
    <RouterLink to="/routines">Routines</RouterLink>
    <RouterLink to="/progress">Progress</RouterLink>
    <RouterLink to="/settings">Settings</RouterLink>
  </nav>
</template>
