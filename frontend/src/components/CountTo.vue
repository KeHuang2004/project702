<template>
  <span>{{ displayValue }}</span>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  startVal: {
    type: Number,
    default: 0
  },
  endVal: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 1000
  }
})

const displayValue = ref(props.startVal)

const startAnimation = () => {
  const startTime = Date.now()
  const startVal = props.startVal
  const endVal = props.endVal
  const duration = props.duration

  const animate = () => {
    const now = Date.now()
    const progress = Math.min((now - startTime) / duration, 1)

    displayValue.value = Math.floor(startVal + (endVal - startVal) * progress)

    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }

  requestAnimationFrame(animate)
}

watch(() => props.endVal, () => {
  startAnimation()
})

onMounted(() => {
  startAnimation()
})
</script>
