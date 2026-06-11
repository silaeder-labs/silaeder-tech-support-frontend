<script setup lang="ts">
import { cn } from '@/lib/utils'

interface Props {
  tone?: 'default' | 'danger' | 'soft' | 'success' | 'pink' | 'active'
  size?: 'sm' | 'md' | 'lg'
  active?: boolean
  disabled?: boolean
  ariaLabel?: string
}

const props = withDefaults(defineProps<Props>(), {
  tone: 'default',
  size: 'md',
  active: false,
  disabled: false,
  ariaLabel: undefined,
})

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    type="button"
    :disabled="props.disabled"
    :aria-label="props.ariaLabel"
    :class="
      cn(
        'control-button',
        `control-button--${props.tone}`,
        `control-button--${props.size}`,
        props.active && 'is-active',
      )
    "
    @click="emit('click')"
  >
    <slot />
  </button>
</template>
