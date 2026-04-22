<template>
  <router-view />
</template>

<style>
:root {
  color-scheme: light;
  font-family:
    'Avenir Next',
    'PingFang SC',
    'Microsoft YaHei',
    sans-serif;
  --bg-app:
    radial-gradient(circle at top left, rgba(15, 123, 255, 0.16), transparent 32%),
    radial-gradient(circle at top right, rgba(255, 138, 61, 0.12), transparent 24%),
    linear-gradient(180deg, #f5f8fc 0%, #edf2f8 48%, #f8fafc 100%);
  --panel-glass: rgba(255, 255, 255, 0.78);
  --panel-solid: rgba(255, 255, 255, 0.94);
  --ink-strong: #0f172a;
  --ink-main: #1e293b;
  --ink-soft: #64748b;
  --line-soft: rgba(15, 23, 42, 0.08);
  --brand: #0f7bff;
  --brand-deep: #0959c9;
  --brand-warm: #ff8a3d;
  --brand-ice: #0ea5e9;
  --success: #10b981;
  --danger: #ef4444;
  --shadow-soft: 0 24px 60px rgba(15, 23, 42, 0.12);
  --shadow-card: 0 18px 40px rgba(15, 23, 42, 0.08);
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  color: var(--ink-main);
  background: var(--bg-app);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  color: inherit;
}

button,
input,
textarea {
  font: inherit;
}

.panel-shell {
  background: var(--panel-glass);
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: var(--shadow-soft);
  backdrop-filter: blur(20px);
}

.surface-card {
  background: var(--panel-solid);
  border: 1px solid var(--line-soft);
  border-radius: 24px;
  box-shadow: var(--shadow-card);
}
</style>
