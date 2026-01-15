<template>
  <div class="logs-page">
    <div class="page-header">
      <h1>日志查看</h1>
      <div class="header-actions">
        <label class="auto-scroll-label">
          <input
            v-model="autoScroll"
            type="checkbox"
          />
          <span>自动滚动</span>
        </label>
        <label class="auto-refresh-label">
          <input
            v-model="autoRefresh"
            type="checkbox"
          />
          <span>自动刷新</span>
        </label>
      </div>
    </div>
    
    <div class="logs-controls">
      <div class="filter-section">
        <label>日志级别：</label>
        <select v-model="selectedLevel" class="level-filter">
          <option value="all">全部</option>
          <option value="DEBUG">DEBUG</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>
      <div class="action-buttons">
        <button @click="loadLogs" :disabled="loading" class="action-btn refresh-btn">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button @click="clearLogs" :disabled="clearing" class="action-btn clear-btn">
          {{ clearing ? '清空中...' : '清空日志' }}
        </button>
      </div>
    </div>
    
    <div v-if="loading && logs.length === 0" class="loading-container">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    
    <template v-else>
      <div v-if="error" class="error-container">
        <div class="error-message">
          <strong>错误：</strong>{{ error }}
        </div>
        <button @click="loadLogs" class="retry-btn">重试</button>
      </div>
      
      <div
        v-else
        ref="logsContainer"
        class="logs-list"
      >
      <div
        v-for="log in filteredLogs"
        :key="`${log.ts}-${log.msg}`"
        class="log-entry"
        :class="log.level.toLowerCase()"
      >
        <span class="log-time">{{ formatTime(log.ts) }}</span>
        <span class="log-level" :class="`level-${log.level.toLowerCase()}`">
          {{ log.level }}
        </span>
        <span class="log-msg">{{ log.msg }}</span>
      </div>
      <div v-if="filteredLogs.length === 0" class="empty-logs">
        没有符合条件的日志
      </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { logsApi } from '../api/logs'
import type { LogEntry } from '../types/api'

const logs = ref<LogEntry[]>([])
const loading = ref(true)  // 初始为 true，确保页面加载时显示加载状态
const clearing = ref(false)
const error = ref<string | null>(null)
const selectedLevel = ref<string>('all')
const autoScroll = ref(true)
const autoRefresh = ref(false)
const logsContainer = ref<HTMLElement | null>(null)

let refreshInterval: number | null = null

const filteredLogs = computed(() => {
  if (selectedLevel.value === 'all') {
    return logs.value
  }
  return logs.value.filter(log => log.level === selectedLevel.value)
})

const loadLogs = async () => {
  try {
    loading.value = true
    error.value = null
    // 后端限制最大 400 条，使用 400 而不是 500
    const result = await logsApi.getLogs(400)
    
    // 确保 result 有 logs 属性
    if (result && result.logs && Array.isArray(result.logs)) {
      // 后端已经返回倒序（最新的在前），直接使用
      logs.value = result.logs
    } else if (Array.isArray(result)) {
      // 如果直接返回数组（向后兼容）
      logs.value = result
    } else {
      logs.value = []
    }
    
    if (autoScroll.value) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  } catch (e: any) {
    console.error('加载日志失败:', e)
    error.value = e.message || e.detail || '加载失败'
    logs.value = []
  } finally {
    loading.value = false
  }
}

const clearLogs = async () => {
  if (!confirm('确定要清空所有日志吗？此操作不可恢复。')) {
    return
  }
  
  try {
    clearing.value = true
    await logsApi.clearLogs()
    logs.value = []
  } catch (e: any) {
    alert('清空失败: ' + (e.message || '未知错误'))
  } finally {
    clearing.value = false
  }
}

const scrollToBottom = () => {
  if (logsContainer.value) {
    logsContainer.value.scrollTop = logsContainer.value.scrollHeight
  }
}

const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp * 1000)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

watch(autoRefresh, (enabled) => {
  if (enabled) {
    refreshInterval = window.setInterval(loadLogs, 5000)
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
})

watch(autoScroll, (enabled) => {
  if (enabled) {
    nextTick(() => {
      scrollToBottom()
    })
  }
})

onMounted(() => {
  loadLogs()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.logs-page {
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

.header-actions {
  display: flex;
  gap: 16px;
}

.auto-scroll-label,
.auto-refresh-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #2c3e50;
  cursor: pointer;
}

.auto-scroll-label input,
.auto-refresh-label input {
  cursor: pointer;
}

.logs-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.filter-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-section label {
  font-size: 14px;
  color: #2c3e50;
}

.level-filter {
  padding: 6px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.refresh-btn {
  background: #3498db;
  color: white;
}

.refresh-btn:hover:not(:disabled) {
  background: #2980b9;
}

.clear-btn {
  background: #e74c3c;
  color: white;
}

.clear-btn:hover:not(:disabled) {
  background: #c0392b;
}

.action-btn:disabled {
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

.logs-list {
  background: white;
  border-radius: 8px;
  padding: 16px;
  max-height: 600px;
  overflow-y: auto;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-entry {
  padding: 8px 12px;
  border-bottom: 1px solid #ecf0f1;
  display: grid;
  grid-template-columns: 180px 80px 1fr;
  gap: 12px;
  align-items: start;
  transition: background 0.1s;
}

.log-entry:hover {
  background: #f8f9fa;
}

.log-entry.error {
  background: #fee;
  border-left: 3px solid #e74c3c;
}

.log-entry.warning {
  background: #fff9e6;
  border-left: 3px solid #f39c12;
}

.log-entry.info {
  border-left: 3px solid #3498db;
}

.log-entry.debug {
  border-left: 3px solid #95a5a6;
}

.log-time {
  color: #7f8c8d;
  font-size: 12px;
  white-space: nowrap;
}

.log-level {
  font-weight: 600;
  font-size: 12px;
  text-align: center;
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

.level-error {
  background: #e74c3c;
  color: white;
}

.level-warning {
  background: #f39c12;
  color: white;
}

.level-info {
  background: #3498db;
  color: white;
}

.level-debug {
  background: #95a5a6;
  color: white;
}

.log-msg {
  color: #2c3e50;
  word-break: break-word;
}

.empty-logs {
  text-align: center;
  padding: 40px;
  color: #7f8c8d;
  font-size: 14px;
}
</style>
