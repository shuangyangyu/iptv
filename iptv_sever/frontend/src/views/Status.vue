<template>
  <div class="status-page">
    <div class="page-header">
      <h1>系统状态</h1>
      <button @click="loadStatus" :disabled="loading" class="refresh-btn">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </div>
    
    <div v-if="loading && !status.m3u.exists && !status.epg.exists" class="loading-container">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
    
    <div v-if="error" class="error-container">
      <div class="error-message">
        <strong>警告：</strong>{{ error }}
      </div>
      <button @click="loadStatus" class="retry-btn">重试</button>
    </div>
    
    <div v-if="!loading || status.m3u.exists || status.epg.exists || iptvNetwork.name || localNetwork.name || cronStatus.enabled || catchupConfig" class="status-grid">
      <div class="status-card">
        <div class="card-header">
          <h2>M3U 文件</h2>
          <span :class="['status-badge', status.m3u.exists ? 'success' : 'warning']">
            {{ status.m3u.exists ? '存在' : '不存在' }}
          </span>
        </div>
        <div v-if="status.m3u.exists" class="card-content">
          <div class="info-item">
            <span class="label">文件大小：</span>
            <span class="value">{{ formatSize(status.m3u.size) }}</span>
          </div>
          <div class="info-item">
            <span class="label">修改时间：</span>
            <span class="value">{{ formatTime(status.m3u.mtime) }}</span>
          </div>
          <div v-if="status.m3u.download_url" class="info-item">
            <span class="label">下载链接：</span>
            <a :href="status.m3u.download_url" target="_blank" class="download-link" title="点击下载 M3U 文件">
              {{ status.m3u.download_url }}
            </a>
          </div>
        </div>
      </div>
      
      <div class="status-card">
        <div class="card-header">
          <h2>EPG 文件</h2>
          <span :class="['status-badge', status.epg.exists ? 'success' : 'warning']">
            {{ status.epg.exists ? '存在' : '不存在' }}
          </span>
        </div>
        <div v-if="status.epg.exists" class="card-content">
          <div class="info-item">
            <span class="label">文件大小：</span>
            <span class="value">{{ formatSize(status.epg.size) }}</span>
          </div>
          <div class="info-item">
            <span class="label">修改时间：</span>
            <span class="value">{{ formatTime(status.epg.mtime) }}</span>
          </div>
          <div v-if="status.epg.download_url" class="info-item">
            <span class="label">下载链接：</span>
            <a :href="status.epg.download_url" target="_blank" class="download-link" title="点击下载 EPG 文件">
              {{ status.epg.download_url }}
            </a>
          </div>
        </div>
      </div>
      
      <div class="status-card">
        <div class="card-header">
          <h2>网络信息</h2>
        </div>
        <div class="card-content">
          <!-- IPTV 网络 -->
          <div class="network-section">
            <h3 class="network-section-title">IPTV 网络</h3>
            <div class="network-info">
              <div class="info-item">
                <span class="label">本地地址：</span>
                <span class="value">{{ iptvNetwork.ip || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">服务网关：</span>
                <span class="value">{{ iptvNetwork.gateway || '-' }}</span>
              </div>
            </div>
          </div>
          
          <!-- 本地网络 -->
          <div class="network-section">
            <h3 class="network-section-title">本地网络</h3>
            <div class="network-info">
              <div class="info-item">
                <span class="label">本地地址：</span>
                <span class="value">{{ localNetwork.ip || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="label">本地网关：</span>
                <span class="value">{{ localNetwork.gateway || '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="status-card">
        <div class="card-header">
          <h2>定时任务</h2>
          <span :class="['status-badge', cronStatus.enabled ? 'enabled' : 'disabled']">
            {{ cronStatus.enabled ? '已启用' : '未启用' }}
          </span>
        </div>
        <div class="card-content">
          <div v-if="cronStatus.enabled" class="status-info">
            <div v-if="cronStatus.cron_expr" class="info-item">
              <span class="label">Cron 表达式：</span>
              <span class="value code">{{ cronStatus.cron_expr }}</span>
            </div>
            <div v-if="cronStatus.next_run_info" class="info-item">
              <span class="label">下次执行：</span>
              <span class="value">{{ cronStatus.next_run_info }}</span>
            </div>
          </div>
          <div v-else class="empty-status">
            未配置定时任务
          </div>
        </div>
      </div>
      
      <div v-if="status.udpxy" class="status-card">
        <div class="card-header">
          <h2>UDPXY 服务</h2>
          <span :class="['status-badge', status.udpxy.running ? 'success' : 'warning']">
            {{ status.udpxy.running ? '运行中' : '已停止' }}
          </span>
        </div>
        <div class="card-content">
          <div class="status-info">
            <div class="info-item">
              <span class="label">运行状态：</span>
              <span :class="['value', status.udpxy.running ? 'success' : 'error']">
                {{ status.udpxy.running ? '运行中' : '已停止' }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">进程端口：</span>
              <span class="value">{{ status.udpxy.port }}</span>
            </div>
            <div class="info-item">
              <span class="label">监听地址：</span>
              <span class="value">{{ status.udpxy.bind_address }}</span>
            </div>
            <div class="info-item">
              <span class="label">IPTV 网络：</span>
              <span class="value">{{ status.udpxy.source_iface }}</span>
            </div>
            <div v-if="status.udpxy.running && status.udpxy.uptime" class="info-item">
              <span class="label">运行时间：</span>
              <span class="value">{{ formatUptime(status.udpxy.uptime) }}</span>
            </div>
            <div v-if="udpxyStatusUrl" class="info-item">
              <span class="label">状态链接：</span>
              <a :href="udpxyStatusUrl" target="_blank" class="download-link" title="点击查看 UDPXY 状态">
                {{ udpxyStatusUrl }}
              </a>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 回放配置卡片 -->
      <div v-if="catchupConfig" class="status-card">
        <div class="card-header">
          <h2>回放服务配置</h2>
          <span class="status-badge success">已配置</span>
        </div>
        <div class="card-content">
          <div class="status-info">
            <div class="info-item">
              <span class="label">服务地址：</span>
              <span class="value code">{{ catchupConfig.target_host }}:{{ catchupConfig.target_port }}</span>
            </div>
            <div v-if="catchupConfig.virtual_domain" class="info-item">
              <span class="label">虚拟域名：</span>
              <span class="value code">{{ catchupConfig.virtual_domain }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { statusApi } from '../api/status'
import { interfacesApi } from '../api/interfaces'
import { configApi } from '../api/config'
import { cronApi } from '../api/cron'
import type { StatusResponse } from '../types/api'
import type { ConfigResponse, CatchupConfigResponse } from '../types/api'
import type { NetworkInterfaceDetailResponse } from '../types/api'
import type { CronStatusResponse } from '../types/api'

const loading = ref(true)
const error = ref<string | null>(null)
const status = ref<StatusResponse>({
  m3u: { exists: false, size: 0, mtime: 0 },
  epg: { exists: false, size: 0, mtime: 0 },
})
const iptvNetwork = ref<NetworkInterfaceDetailResponse>({
  name: '',
  ip: null,
  gateway: null,
  has_ip: false,
})
const localNetwork = ref<NetworkInterfaceDetailResponse>({
  name: '',
  ip: null,
  gateway: null,
  has_ip: false,
})
const cronStatus = ref<CronStatusResponse>({
  enabled: false,
  cron_expr: null,
  cron_cmd: null,
  next_run_info: null,
})
const catchupConfig = ref<CatchupConfigResponse | null>(null)
const udpxyStatusUrl = ref<string | null>(null)

const loadStatus = async () => {
  try {
    loading.value = true
    error.value = null
    
    // 并行加载所有数据，即使某个失败也不影响其他数据
    const results = await Promise.allSettled([
      statusApi.getStatus(),
      configApi.getConfig().catch(() => null),
      interfacesApi.getInterfaceStatus('source_iface,local_iface').catch(() => ({ interfaces: [] })),
      cronApi.getStatus().catch(() => ({ enabled: false, cron_expr: null, cron_cmd: null, next_run_info: null })),
    ])
    
    // 处理状态数据
    if (results[0].status === 'fulfilled') {
      status.value = results[0].value
      error.value = null
    } else {
      console.error('状态数据加载失败:', results[0].reason)
      // 状态数据失败时，保持默认值，只显示警告信息
      error.value = '状态数据加载失败，部分信息可能不准确: ' + (results[0].reason?.message || '未知错误')
    }
    
    // 处理配置数据（用于获取回放配置和 UDPXY 状态链接）
    if (results[1].status === 'fulfilled' && results[1].value) {
      const config: ConfigResponse = results[1].value
      catchupConfig.value = config.catchup || null
    } else {
      console.error('配置数据加载失败:', results[1].reason)
      catchupConfig.value = null
    }
    
    // 处理网络数据
    if (results[2].status === 'fulfilled') {
      const response = results[2].value
      const interfaces = response.interfaces || []
      
      // API 默认返回的顺序是：source_iface, local_iface
      // 第一个接口是IPTV网络（source_iface）
      iptvNetwork.value = interfaces[0] || { name: '', ip: null, gateway: null, has_ip: false }
      
      // 第二个接口是本地网络（local_iface）
      localNetwork.value = interfaces[1] || { name: '', ip: null, gateway: null, has_ip: false }
    } else {
      console.error('网络数据加载失败:', results[2].reason)
      iptvNetwork.value = { name: '', ip: null, gateway: null, has_ip: false }
      localNetwork.value = { name: '', ip: null, gateway: null, has_ip: false }
    }
    
    // 处理定时任务数据
    if (results[3].status === 'fulfilled') {
      cronStatus.value = results[3].value
    } else {
      console.error('定时任务数据加载失败:', results[3].reason)
      cronStatus.value = { enabled: false, cron_expr: null, cron_cmd: null, next_run_info: null }
    }
    
    // 计算 UDPXY 状态链接 URL（在所有数据加载完成后计算）
    if (results[1].status === 'fulfilled' && results[1].value) {
      const config: ConfigResponse = results[1].value
      if (config.udpxy_base) {
        udpxyStatusUrl.value = `${config.udpxy_base}/status`
      } else if (status.value.udpxy && localNetwork.value.ip) {
        // 如果 udpxy_base 不存在，使用 UDPXY 端口和本地网络 IP
        const port = status.value.udpxy.port || 4022
        udpxyStatusUrl.value = `http://${localNetwork.value.ip}:${port}/status`
      } else {
        udpxyStatusUrl.value = null
      }
    } else {
      udpxyStatusUrl.value = null
    }
  } catch (e: any) {
    console.error('加载状态失败:', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN')
}

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

let refreshInterval: number | null = null

onMounted(() => {
  loadStatus()
  // 每30秒刷新一次
  refreshInterval = window.setInterval(loadStatus, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.status-page {
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

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.status-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s;
}

.status-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
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

.status-badge.success {
  background: #d4edda;
  color: #155724;
}

.status-badge.warning {
  background: #fff3cd;
  color: #856404;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.label {
  color: #7f8c8d;
  font-size: 14px;
  min-width: 80px;
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

.status-badge.enabled {
  background: #d4edda;
  color: #155724;
}

.status-badge.disabled {
  background: #f8d7da;
  color: #721c24;
}

.value.code {
  font-family: 'Courier New', monospace;
  background: #f8f9fa;
  padding: 4px 8px;
  border-radius: 4px;
}

.empty-status {
  color: #7f8c8d;
  font-style: italic;
  padding: 20px;
  text-align: center;
}

.network-section {
  margin-bottom: 20px;
}

.network-section:last-child {
  margin-bottom: 0;
}

.network-section-title {
  font-size: 1rem;
  color: #34495e;
  margin: 0 0 12px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #ecf0f1;
  font-weight: 600;
}

.download-link {
  color: #3498db;
  text-decoration: none;
  font-size: 13px;
  word-break: break-all;
  transition: color 0.2s;
}

.download-link:hover {
  color: #2980b9;
  text-decoration: underline;
}

.download-url-item {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.download-link-container {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.download-link {
  flex: 1;
  min-width: 0;
  word-break: break-all;
}

.copy-btn {
  padding: 4px 12px;
  background: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  transition: background 0.2s;
}

.copy-btn:hover {
  background: #2980b9;
}

.copy-btn:active {
  background: #21618c;
}

.network-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
</style>

