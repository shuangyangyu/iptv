import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'

// 错误处理
window.addEventListener('error', (event) => {
  console.error('全局错误:', event.error)
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('未处理的 Promise 拒绝:', event.reason)
})

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// 确保 DOM 元素存在后再挂载
const appElement = document.getElementById('app')

if (appElement) {
  try {
    app.mount('#app')
    // 挂载成功后才移除加载提示
    const loadingFallback = document.getElementById('loading-fallback')
    if (loadingFallback) {
      loadingFallback.remove()
    }
  } catch (error) {
    console.error('Vue 应用挂载失败:', error)
    // 保持加载提示显示
  }
} else {
  console.error('找不到 #app 元素')
  document.body.innerHTML = '<div style="padding: 20px; color: red; font-size: 16px;">错误：找不到 #app 元素。请检查 index.html 文件。</div>'
}

