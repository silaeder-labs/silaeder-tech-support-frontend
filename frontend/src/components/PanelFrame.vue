<script setup lang="ts">
interface Props {
  title?: string
  page?: boolean
}

withDefaults(defineProps<Props>(), {
  title: '',
  page: false,
})
</script>

<template>
  <section :class="['panel-frame', page && 'panel-frame--page']" :aria-label="title">
    <slot />
  </section>
</template>
