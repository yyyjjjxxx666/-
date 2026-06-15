<template>
  <div class="skeleton-loader" :class="[`skeleton-${type}`, { animated: animated }]">
    <!-- Text Skeleton -->
    <template v-if="type === 'text'">
      <div v-for="i in count" :key="i" class="skeleton-line" :style="{ width: getRandomWidth(i) }" />
    </template>

    <!-- Card Skeleton -->
    <template v-if="type === 'card'">
      <div v-for="i in count" :key="i" class="skeleton-card">
        <div class="skeleton-card-image" />
        <div class="skeleton-card-body">
          <div class="skeleton-line" style="width: 60%" />
          <div class="skeleton-line" style="width: 90%" />
          <div class="skeleton-line" style="width: 40%" />
        </div>
      </div>
    </template>

    <!-- Table Row Skeleton -->
    <template v-if="type === 'table'">
      <div v-for="i in count" :key="i" class="skeleton-table-row">
        <div v-for="col in columns" :key="col" class="skeleton-cell" :style="{ width: 100 / columns + '%' }">
          <div class="skeleton-line" :style="{ width: getRandomWidth(i + col * 10) }" />
        </div>
      </div>
    </template>

    <!-- Avatar Skeleton -->
    <template v-if="type === 'avatar'">
      <div class="skeleton-avatar" :style="{ width: size + 'px', height: size + 'px' }" />
    </template>

    <!-- Stat Card Skeleton -->
    <template v-if="type === 'stat'">
      <div v-for="i in count" :key="i" class="skeleton-stat">
        <div class="skeleton-line" style="width: 50%; height: 14px" />
        <div class="skeleton-line" style="width: 35%; height: 28px; margin-top: 8px" />
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  type: { type: String, default: 'text', validator: v => ['text', 'card', 'table', 'avatar', 'stat'].includes(v) },
  count: { type: Number, default: 3 },
  columns: { type: Number, default: 4 },
  size: { type: Number, default: 48 },
  animated: { type: Boolean, default: true }
})

const widths = ['85%', '60%', '92%', '45%', '75%', '55%', '88%', '40%']
function getRandomWidth(seed) {
  return widths[seed % widths.length]
}
</script>

<style scoped>
.skeleton-loader {
  width: 100%;
}

/* ── Skeleton Line ── */
.skeleton-line {
  height: 12px;
  border-radius: var(--radius-sm);
  background: var(--color-gray-200);
  margin-bottom: 8px;
}

/* ── Animated Shimmer ── */
.animated .skeleton-line,
.animated .skeleton-card-image,
.animated .skeleton-avatar {
  background: linear-gradient(
    90deg,
    var(--color-gray-100) 25%,
    var(--color-gray-50) 50%,
    var(--color-gray-100) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* ── Card Skeleton ── */
.skeleton-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  overflow: hidden;
  margin-bottom: 16px;
}
.skeleton-card-image {
  height: 140px;
  background: var(--color-gray-200);
}
.skeleton-card-body {
  padding: 16px;
}

/* ── Table Row Skeleton ── */
.skeleton-table-row {
  display: flex;
  gap: 16px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-light);
}
.skeleton-cell {
  flex: 1;
}
.skeleton-cell .skeleton-line {
  margin-bottom: 0;
}

/* ── Avatar Skeleton ── */
.skeleton-avatar {
  border-radius: var(--radius-full);
  background: var(--color-gray-200);
  display: inline-block;
}

/* ── Stat Card Skeleton ── */
.skeleton-stat {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-light);
  padding: 20px;
  text-align: center;
}
.skeleton-stat .skeleton-line {
  margin-left: auto;
  margin-right: auto;
}

/* ── Dark Mode ── */
[data-theme="dark"] .skeleton-card {
  background: var(--bg-card);
  border-color: var(--border-light);
}
[data-theme="dark"] .animated .skeleton-line,
[data-theme="dark"] .animated .skeleton-card-image,
[data-theme="dark"] .animated .skeleton-avatar {
  background: linear-gradient(
    90deg,
    rgba(148, 163, 184, 0.08) 25%,
    rgba(148, 163, 184, 0.04) 50%,
    rgba(148, 163, 184, 0.08) 75%
  );
  background-size: 200% 100%;
}
[data-theme="dark"] .skeleton-stat {
  background: var(--bg-card);
}
</style>
