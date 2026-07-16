<template>
  <header class="module-header">
    <div>
      <div class="module-header__eyebrow">STEEL DEFECT AI PLATFORM</div>
      <h1>{{ title }}</h1>
      <p>{{ description }}</p>
    </div>
    <div class="module-header__actions">
      <slot />
    </div>
  </header>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: "" },
});
</script>

<style lang="scss" scoped>
.module-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: $spacing-lg;
  margin-bottom: $spacing-lg;

  h1 {
    margin: 3px 0 8px;
    color: #172033;
    font-size: 28px;
    line-height: 1.25;
  }

  p {
    max-width: 760px;
    margin: 0;
    color: $text-secondary;
    line-height: 1.65;
  }
}

.module-header__eyebrow {
  color: #667085;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.module-header__actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding-top: 4px;
  white-space: nowrap;
}

@media (max-width: 780px) {
  .module-header {
    flex-direction: column;
  }
}
</style>
