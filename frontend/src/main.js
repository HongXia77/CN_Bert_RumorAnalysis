import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import Particles from "@tsparticles/vue3"
import { loadFull } from "tsparticles"

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus)
app.use(Particles, {
  init: async engine => {
    await loadFull(engine) // 加载完整的粒子功能
  },
})
app.mount('#app')
