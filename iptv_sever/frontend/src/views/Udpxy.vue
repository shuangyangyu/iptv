<template>
  <div class="udpxy-page">
    <div class="page-header">
      <h1>UDPXY 管理</h1>
      <button @click="loadStatus" :disabled="loading" class="refresh-btn">
        {{ loading ? '加载中...' : '刷新' }}
      </button>
    </div>
    
    <div v-if="loading" class="loading-container">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    
    <div v-else-if="error" class="error-container">
      <div class="error-message">
        <strong>错误：</strong>{{ error }}
      </div>
      <button @click="loadStatus" class="retry-btn">重试</button>
    </div>
    
    <div v-else class="udpxy-content">
      <div class="status-card">
        <div class="card-header">
          <h2>服务状态</h2>
          <span :class="['status-badge', udpxyStatus.running ? 'running' : 'stopped']">
            {{ udpxyStatus.running ? '运行中' : '已停止' }}
          </span>
        </div>
        <div class="card-content">
          <div class="status-grid">
            <div class="info-item">
              <span class="label">运行状态：</span>
              <span :class="['value', udpxyStatus.running ? 'success' : 'error']">
                {{ udpxyStatus.running ? '运行中' : '已停止' }}
              </span>
            </div>
            <div v-if="udpxyStatus.running && udpxyStatus.pid" class="info-item">
              <span class="label">进程 ID：</span>
              <span class="value code">{{ udpxyStatus.pid }}</span>
            </div>
            <div class="info-item">
              <span class="label">端口：</span>
              <span class="value">{{ udpxyStatus.port }}</span>
            </div>
            <div class="info-item">
              <span class="label">本地监听：</span>
              <span class="value">{{ udpxyStatus.bind_address }}</span>
            </div>
            <div class="info-item">
              <span class="label">IPTV 网络：</span>
              <span class="value">{{ udpxyStatus.source_iface }}</span>
            </div>
            <div class="info-item">
              <span class="label">最大连接数：</span>
              <span class="value">{{ udpxyStatus.max_connections }}</span>
            </div>
            <div v-if="udpxyStatus.running" class="info-item">
              <span class="label">当前连接数：</span>
              <span class="value">{{ udpxyStatus.connections }}</span>
            </div>
            <div v-if="udpxyStatus.running && udpxyStatus.uptime" class="info-item">
              <span class="label">运行时间：</span>
              <span class="value">{{ formatUptime(udpxyStatus.uptime) }}</span>
            </div>
            <div class="info-item">
              <span class="label">可用性：</span>
              <span :class="['value', udpxyStatus.available ? 'success' : 'error']">
                {{ udpxyStatus.available ? '可用' : '不可用' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { udpxyApi } from '../api/udpxy'
import type { UdpxyStatusResponse } from '../types/api'

const loading = ref(false)
const error = ref<string | null>(null)

const udpxyStatus = ref<UdpxyStatusResponse>({
  running: false,
  pid: null,
  port: 4022,
  bind_address: '0.0.0.0',
  source_iface: 'eth1',
  max_connections: 5,
  connections: 0,
  uptime: 0,
  available: false,
})

let statusInterval: number | null = null

const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (days > 0) {
    return `${days}天 ${hours}小时 ${minutes}分钟`
  } else if (hours > 0) {
    return `${hours}小时 ${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟 ${secs}秒`
  } else {
    return `${secs}秒`
  }
}

const loadStatus = async (isInitialLoad = false) => {
  // 保存当前滚动位置
  const scrollY = window.scrollY
  
  try {
    // 只在首次加载时显示加载状态，自动刷新时不显示
    if (isInitialLoad) {
      loading.value = true
    }
    error.value = null
    udpxyStatus.value = await udpxyApi.getStatus()
  } catch (e: any) {
    // 只在首次加载时显示错误，自动刷新时静默失败
    if (isInitialLoad) {
      error.value = e.message || '加载失败'
    } else {
      console.error('自动刷新失败:', e)
    }
  } finally {
    loading.value = false
    // 恢复滚动位置（使用 nextTick 确保 DOM 更新完成）
    nextTick(() => {
      if (scrollY > 0) {
        window.scrollTo({
          top: scrollY,
          behavior: 'instant' as ScrollBehavior
        })
      }
    })
  }
}




// 滚动事件处理函数
let handleScroll: (() => void) | null = null
let scrollSaveTimer: number | null = null

// 保存滚动位置的函数（防抖）
const saveScrollPosition = () => {
  if (scrollSaveTimer) {
    clearTimeout(scrollSaveTimer)
  }
  scrollSaveTimer = window.setTimeout(() => {
    sessionStorage.setItem('udpxy_scroll_y', String(window.scrollY))
  }, 100)
}

onMounted(() => {
  loadStatus(true) // 首次加载，显示加载状态
  // 每5秒刷新一次状态（静默刷新，不显示加载状态）
  statusInterval = window.setInterval(() => loadStatus(false), 5000)
  
  // 监听滚动事件，保存滚动位置（防抖）
  handleScroll = saveScrollPosition
  window.addEventListener('scroll', handleScroll, { passive: true })
  
  // 在页面卸载前保存滚动位置
  window.addEventListener('beforeunload', saveScrollPosition)
  
  // 延迟恢复滚动位置，确保页面内容已渲染
  // 使用 nextTick 和 setTimeout 组合，确保 DOM 完全渲染后再恢复
  nextTick(() => {
    setTimeout(() => {
      const savedScrollY = sessionStorage.getItem('udpxy_scroll_y')
      if (savedScrollY) {
        const scrollY = parseInt(savedScrollY, 10)
        if (scrollY > 0) {
          // 使用 instant 行为，避免滚动动画
          window.scrollTo({
            top: scrollY,
            behavior: 'instant' as ScrollBehavior
          })
          // 清除保存的位置，避免下次进入页面时再次恢复
          sessionStorage.removeItem('udpxy_scroll_y')
        }
      }
    }, 200)
  })
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
  // 清理滚动事件监听器
  if (handleScroll) {
    window.removeEventListener('scroll', handleScroll)
  }
  // 清理定时器
  if (scrollSaveTimer) {
    clearTimeout(scrollSaveTimer)
  }
  // 保存当前滚动位置
  saveScrollPosition()
  window.removeEventListener('beforeunload', saveScrollPosition)
})
</script>

<style scoped>
.udpxy-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin: 0;
}

.refresh-btn {
  padding: 8px 16px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #2980b9;
}

.refresh-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-container {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.error-message {
  color: #e74c3c;
  margin-bottom: 16px;
  padding: 12px;
  background: #fee;
  border-radius: 4px;
  border-left: 4px solid #e74c3c;
}

.retry-btn {
  padding: 8px 16px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}

.retry-btn:hover {
  background: #c0392b;
}

.udpxy-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.status-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ecf0f1;
}

.card-header h2 {
  font-size: 1.2rem;
  color: #2c3e50;
  margin: 0;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.running {
  background: #d4edda;
  color: #155724;
}

.status-badge.stopped {
  background: #f8d7da;
  color: #721c24;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.label {
  color: #7f8c8d;
  font-size: 14px;
  min-width: 120px;
}

.value {
  color: #2c3e50;
  font-size: 14px;
  font-weight: 500;
}

.value.success {
  color: #27ae60;
}

.value.error {
  color: #e74c3c;
}

.value.code {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
}

.control-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.control-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

.start-btn {
  background: #27ae60;
  color: white;
}

.start-btn:hover:not(:disabled) {
  background: #229954;
}

.stop-btn {
  background: #e74c3c;
  color: white;
}

.stop-btn:hover:not(:disabled) {
  background: #c0392b;
}

.restart-btn {
  background: #f39c12;
  color: white;
}

.restart-btn:hover:not(:disabled) {
  background: #e67e22;
}

.control-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.operation-message {
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
}

.operation-message.success {
  background: #d4edda;
  color: #155724;
  border-left: 4px solid #27ae60;
}

.operation-message.error {
  background: #fee;
  color: #721c24;
  border-left: 4px solid #e74c3c;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #2c3e50;
  font-weight: 500;
  font-size: 14px;
}

.form-input {
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.form-input:disabled {
  background: #f8f9fa;
  cursor: not-allowed;
}

.field-hint {
  font-size: 12px;
  color: #7f8c8d;
}

.success-message {
  padding: 12px 16px;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
  border-left: 4px solid #27ae60;
}

.error-message {
  padding: 12px 16px;
  background: #fee;
  color: #721c24;
  border-radius: 4px;
  border-left: 4px solid #e74c3c;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
  padding-top: 20px;
  border-top: 1px solid #ecf0f1;
}

.submit-btn {
  padding: 10px 24px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #229954;
}

.submit-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.reset-btn {
  padding: 10px 24px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.reset-btn:hover:not(:disabled) {
  background: #7f8c8d;
}

.reset-btn:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}
</style>
