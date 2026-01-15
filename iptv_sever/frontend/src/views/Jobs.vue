<template>
  <div class="jobs-page">
    <div class="page-header">
      <h1>任务执行</h1>
    </div>
    
    <div class="jobs-content">
      <div class="job-card">
        <div class="card-header">
          <h2>选择任务类型</h2>
        </div>
        <div class="job-buttons">
          <button
            @click="runJob('m3u')"
            :disabled="running"
            class="job-btn m3u-btn"
          >
            <span class="btn-icon">📄</span>
            <span class="btn-text">生成 M3U</span>
            <span v-if="running && currentJob === 'm3u'" class="btn-loading">执行中...</span>
          </button>
          <button
            @click="runJob('epg')"
            :disabled="running"
            class="job-btn epg-btn"
          >
            <span class="btn-icon">📺</span>
            <span class="btn-text">生成 EPG</span>
            <span v-if="running && currentJob === 'epg'" class="btn-loading">执行中...</span>
          </button>
          <button
            @click="runJob('logos')"
            :disabled="running"
            class="job-btn logos-btn"
          >
            <span class="btn-icon">🖼️</span>
            <span class="btn-text">下载 Logos</span>
            <span v-if="running && currentJob === 'logos'" class="btn-loading">执行中...</span>
          </button>
          <button
            @click="generateAll"
            :disabled="running"
            class="job-btn generate-all-btn"
          >
            <span class="btn-icon">⚡</span>
            <span class="btn-text">一键生成</span>
            <span v-if="running && currentJob === 'all'" class="btn-loading">执行中...</span>
          </button>
        </div>
      </div>
      
      <div class="job-card">
        <div class="card-header">
          <h2>系统检测</h2>
        </div>
        <div class="job-buttons">
          <button
            @click="checkEnvironment"
            :disabled="testing"
            class="job-btn check-environment-btn"
          >
            <span class="btn-icon">🔍</span>
            <span class="btn-text">环境监测</span>
            <span v-if="testing && currentTest === 'environment'" class="btn-loading">检测中...</span>
          </button>
        </div>
      </div>
      
      <div class="job-card">
        <div class="card-header">
          <h2>UDPXY 服务控制</h2>
        </div>
        <div class="job-buttons">
          <button
            @click="startUdpxy"
            :disabled="udpxyOperating || (udpxyStatus && udpxyStatus.running)"
            class="job-btn udpxy-start-btn"
          >
            <span class="btn-icon">▶️</span>
            <span class="btn-text">启动服务</span>
            <span v-if="udpxyStarting" class="btn-loading">启动中...</span>
          </button>
          <button
            @click="stopUdpxy"
            :disabled="udpxyOperating || !udpxyStatus || !udpxyStatus.running"
            class="job-btn udpxy-stop-btn"
          >
            <span class="btn-icon">⏹️</span>
            <span class="btn-text">停止服务</span>
            <span v-if="udpxyStopping" class="btn-loading">停止中...</span>
          </button>
          <button
            @click="restartUdpxy"
            :disabled="udpxyOperating"
            class="job-btn udpxy-restart-btn"
          >
            <span class="btn-icon">🔄</span>
            <span class="btn-text">重启服务</span>
            <span v-if="udpxyRestarting" class="btn-loading">重启中...</span>
          </button>
        </div>
        <div v-if="udpxyOperationMessage" class="operation-message" :class="udpxyOperationSuccess ? 'success' : 'error'">
          {{ udpxyOperationMessage }}
        </div>
      </div>
      
      <div v-if="running" class="status-card running-card">
        <div class="status-header">
          <div class="status-icon">
            <div class="loading-spinner"></div>
          </div>
          <div class="status-text">
            <h3>任务执行中</h3>
            <p>正在执行 {{ getJobName(currentJob) }} 任务，请稍候...</p>
          </div>
        </div>
      </div>
      
      <div v-if="jobResult" class="status-card success-card">
        <div class="status-header">
          <div class="status-icon">✅</div>
          <div class="status-text">
            <h3>任务执行成功</h3>
            <p v-if="jobResult.message">{{ jobResult.message }}</p>
            <p v-else>{{ getJobName(currentJob) }} 任务已完成</p>
          </div>
          <button @click="jobResult = null" class="close-btn">×</button>
        </div>
        <div v-if="!jobResult.message" class="result-content">
          <pre>{{ formatResult(jobResult) }}</pre>
        </div>
      </div>
      
      <div v-if="jobError" class="status-card error-card">
        <div class="status-header">
          <div class="status-icon">❌</div>
          <div class="status-text">
            <h3>任务执行失败</h3>
            <p>{{ jobError }}</p>
          </div>
          <button @click="jobError = null" class="close-btn">×</button>
        </div>
      </div>
      
      <div v-if="testResult" class="status-card success-card">
        <div class="status-header">
          <div class="status-icon">✅</div>
          <div class="status-text">
            <h3>检测结果</h3>
            <p v-if="testResult.message">{{ testResult.message }}</p>
            <p v-else>检测已完成</p>
          </div>
          <button @click="testResult = null" class="close-btn">×</button>
        </div>
        <div v-if="!testResult.message" class="result-content">
          <pre>{{ formatResult(testResult) }}</pre>
        </div>
      </div>
      
      <div v-if="testError" class="status-card error-card">
        <div class="status-header">
          <div class="status-icon">❌</div>
          <div class="status-text">
            <h3>检测失败</h3>
            <p>{{ testError }}</p>
          </div>
          <button @click="testError = null" class="close-btn">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { jobsApi } from '../api/jobs'
import { systemApi } from '../api/system'
import { configApi } from '../api/config'
import { udpxyApi } from '../api/udpxy'
import type { UdpxyStatusResponse } from '../types/api'

const running = ref(false)
const testing = ref(false)
const currentJob = ref<'m3u' | 'epg' | 'logos' | 'all' | null>(null)
const currentTest = ref<'environment' | null>(null)
const jobResult = ref<any>(null)
const jobError = ref<string | null>(null)
const testResult = ref<any>(null)
const testError = ref<string | null>(null)

// UDPXY 服务控制相关
const udpxyStatus = ref<UdpxyStatusResponse | null>(null)
const udpxyOperating = ref(false)
const udpxyStarting = ref(false)
const udpxyStopping = ref(false)
const udpxyRestarting = ref(false)
const udpxyOperationMessage = ref<string | null>(null)
const udpxyOperationSuccess = ref(false)
let udpxyStatusInterval: number | null = null

const getJobName = (jobType: string | null): string => {
  const names: Record<string, string> = {
    m3u: 'M3U 生成',
    epg: 'EPG 生成',
    logos: 'Logos 下载',
    all: '一键生成',
  }
  return names[jobType || ''] || '任务'
}

const formatResult = (result: any): string => {
  if (typeof result === 'string') {
    return result
  }
  if (result && typeof result === 'object') {
    return JSON.stringify(result, null, 2)
  }
  return String(result)
}

const runJob = async (jobType: 'm3u' | 'epg' | 'logos') => {
  try {
    running.value = true
    currentJob.value = jobType
    jobResult.value = null
    jobError.value = null
    
    await jobsApi.runJob(jobType)
    // 所有任务只显示简单提示，不显示详细结果
    jobResult.value = { message: '生成已完成' }
    
    // 5秒后自动清除成功消息
    setTimeout(() => {
      if (jobResult.value) {
        jobResult.value = null
      }
    }, 5000)
  } catch (e: any) {
    jobError.value = e.message || '任务执行失败'
    jobResult.value = null
  } finally {
    running.value = false
    currentJob.value = null
  }
}

const generateAll = async () => {
  try {
    running.value = true
    currentJob.value = 'all'
    jobResult.value = null
    jobError.value = null
    
    // 先获取配置
    const config = await configApi.getConfig()
    
    // 根据配置判断需要生成哪些文件
    const tasks: Promise<any>[] = []
    const taskNames: string[] = []
    
    // 如果有输入 URL，生成 M3U
    if (config.input_url && config.input_url.trim()) {
      tasks.push(jobsApi.runJob('m3u'))
      taskNames.push('M3U')
    }
    
    // 如果有 EPG 配置，生成 EPG
    if (config.epg_base_url && config.epg_base_url.trim()) {
      tasks.push(jobsApi.runJob('epg'))
      taskNames.push('EPG')
    }
    
    if (tasks.length === 0) {
      jobError.value = '请至少配置 IPTV 源地址或 EPG 查询地址'
      running.value = false
      currentJob.value = null
      return
    }
    
    // 并行执行所有任务
    await Promise.all(tasks)
    
    // 只显示简单提示，不显示详细结果
    jobResult.value = {
      message: '生成已完成'
    }
    
    // 5秒后自动清除成功消息
    setTimeout(() => {
      if (jobResult.value) {
        jobResult.value = null
      }
    }, 5000)
  } catch (e: any) {
    jobError.value = e.message || '一键生成失败'
    jobResult.value = null
  } finally {
    running.value = false
    currentJob.value = null
  }
}

const checkEnvironment = async () => {
  try {
    testing.value = true
    currentTest.value = 'environment'
    testResult.value = null
    testError.value = null
    
    await systemApi.healthCheck()
    // 只显示简单提示，不显示详细结果
    testResult.value = { message: '检测已完成' }
    
    // 5秒后自动清除成功消息
    setTimeout(() => {
      if (testResult.value) {
        testResult.value = null
      }
    }, 5000)
  } catch (e: any) {
    testError.value = e.message || '检测失败'
    testResult.value = null
  } finally {
    testing.value = false
    currentTest.value = null
  }
}

const loadUdpxyStatus = async () => {
  try {
    udpxyStatus.value = await udpxyApi.getStatus()
  } catch (e: any) {
    console.error('加载 UDPXY 状态失败:', e)
  }
}

const startUdpxy = async () => {
  try {
    udpxyOperating.value = true
    udpxyStarting.value = true
    udpxyOperationMessage.value = null
    udpxyOperationSuccess.value = false
    
    const result = await udpxyApi.start()
    console.log('UDPXY 启动结果:', result)
    
    // 检查操作是否成功，并且服务是否正在运行
    if (result.ok && result.running) {
      udpxyOperationMessage.value = result.message || 'UDPXY 服务启动成功'
      udpxyOperationSuccess.value = true
      await loadUdpxyStatus()
      setTimeout(() => {
        udpxyOperationMessage.value = null
      }, 3000)
    } else if (result.ok && !result.running) {
      // 启动命令执行了，但服务没有运行
      udpxyOperationMessage.value = result.message || '启动命令已执行，但服务未运行'
      udpxyOperationSuccess.value = false
      await loadUdpxyStatus()
    } else {
      // 启动失败
      udpxyOperationMessage.value = result.message || '启动失败: 未知错误'
      udpxyOperationSuccess.value = false
    }
  } catch (e: any) {
    console.error('UDPXY 启动异常:', e)
    const errorMessage = e.response?.data?.detail || e.response?.data?.message || e.message || '未知错误'
    udpxyOperationMessage.value = '启动失败: ' + errorMessage
    udpxyOperationSuccess.value = false
  } finally {
    udpxyOperating.value = false
    udpxyStarting.value = false
  }
}

const stopUdpxy = async () => {
  if (!confirm('确定要停止 UDPXY 服务吗？')) {
    return
  }
  
  try {
    udpxyOperating.value = true
    udpxyStopping.value = true
    udpxyOperationMessage.value = null
    await udpxyApi.stop()
    udpxyOperationMessage.value = 'UDPXY 服务已停止'
    udpxyOperationSuccess.value = true
    await loadUdpxyStatus()
    setTimeout(() => {
      udpxyOperationMessage.value = null
    }, 2000)
  } catch (e: any) {
    udpxyOperationMessage.value = '停止失败: ' + (e.message || '未知错误')
    udpxyOperationSuccess.value = false
  } finally {
    udpxyOperating.value = false
    udpxyStopping.value = false
  }
}

const restartUdpxy = async () => {
  if (!confirm('确定要重启 UDPXY 服务吗？')) {
    return
  }
  
  try {
    udpxyOperating.value = true
    udpxyRestarting.value = true
    udpxyOperationMessage.value = null
    await udpxyApi.restart()
    udpxyOperationMessage.value = 'UDPXY 服务重启成功'
    udpxyOperationSuccess.value = true
    await loadUdpxyStatus()
    setTimeout(() => {
      udpxyOperationMessage.value = null
    }, 2000)
  } catch (e: any) {
    udpxyOperationMessage.value = '重启失败: ' + (e.message || '未知错误')
    udpxyOperationSuccess.value = false
  } finally {
    udpxyOperating.value = false
    udpxyRestarting.value = false
  }
}

onMounted(() => {
  loadUdpxyStatus()
  // 每5秒刷新一次 UDPXY 状态
  udpxyStatusInterval = window.setInterval(() => loadUdpxyStatus(), 5000)
})

onUnmounted(() => {
  if (udpxyStatusInterval) {
    clearInterval(udpxyStatusInterval)
  }
})

</script>

<style scoped>
.jobs-page {
  padding: 0;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h1 {
  font-size: 1.8rem;
  color: #2c3e50;
  margin: 0;
}

.jobs-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.job-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #ecf0f1;
}

.card-header h2 {
  font-size: 1.2rem;
  color: #2c3e50;
  margin: 0;
}

.job-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.job-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: white;
  border: 2px solid #ecf0f1;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 16px;
}

.job-btn:hover:not(:disabled) {
  border-color: #3498db;
  background: #f8f9fa;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.job-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.m3u-btn:hover:not(:disabled) {
  border-color: #3498db;
}

.epg-btn:hover:not(:disabled) {
  border-color: #9b59b6;
}

.logos-btn:hover:not(:disabled) {
  border-color: #e67e22;
}

.generate-all-btn:hover:not(:disabled) {
  border-color: #9b59b6;
  background: #f4ecf7;
}

.check-environment-btn:hover:not(:disabled) {
  border-color: #3498db;
  background: #ebf5fb;
}

.btn-icon {
  font-size: 32px;
}

.btn-text {
  font-weight: 500;
  color: #2c3e50;
}

.btn-loading {
  font-size: 12px;
  color: #7f8c8d;
}

.status-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.running-card {
  border-left: 4px solid #3498db;
  background: #ebf5fb;
}

.success-card {
  border-left: 4px solid #27ae60;
  background: #eafaf1;
}

.error-card {
  border-left: 4px solid #e74c3c;
  background: #fdeaea;
}

.status-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.status-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.status-text {
  flex: 1;
}

.status-text h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: #2c3e50;
}

.status-text p {
  margin: 0;
  font-size: 14px;
  color: #7f8c8d;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #7f8c8d;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  flex-shrink: 0;
}

.close-btn:hover {
  color: #2c3e50;
}

.result-content {
  margin-top: 16px;
  padding: 16px;
  background: white;
  border-radius: 4px;
  border: 1px solid #ecf0f1;
}

.result-content pre {
  margin: 0;
  font-size: 12px;
  color: #2c3e50;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.operation-message {
  margin-top: 16px;
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
</style>

