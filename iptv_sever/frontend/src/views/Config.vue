<template>
  <div class="config-page">
    <div class="page-header">
      <h1>配置管理</h1>
      <button @click="loadConfig" :disabled="loading" class="refresh-btn">
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
      <button @click="loadConfig" class="retry-btn">重试</button>
    </div>
    
    <div v-else class="config-card">
      <form @submit.prevent="saveConfig">
        <!-- 基础信息配置分组 -->
        <div class="config-section">
          <h2 class="section-title collapsible" @click="toggleSection('basic')">
            <span class="section-title-text">基础信息配置</span>
            <span class="collapse-icon" :class="{ 'collapsed': !expandedSections.basic }">▼</span>
          </h2>
          <div v-show="expandedSections.basic" class="section-content">
            <div class="form-group">
              <label for="input_url">
                IPTV 源地址
              </label>
              <input
                id="input_url"
                v-model="config.input_url"
                type="text"
                placeholder="例如: http://example.com/playlist.m3u"
                :class="{ 'error': errors.input_url }"
              />
              <span v-if="errors.input_url" class="error-text">{{ errors.input_url }}</span>
            </div>
            
            <div class="form-group">
              <label for="source_iface">
                IPTV 网络接口
                <span v-if="physicalInterfacesLoading" class="field-hint">(加载中...)</span>
              </label>
              <div class="interface-select-wrapper" style="position: relative;">
                <input
                  id="source_iface"
                  v-model="config.source_iface"
                  type="text"
                  list="source-iface-custom-list"
                  placeholder="输入自定义网卡名称"
                  :class="{ 'error': errors.source_iface }"
                  :disabled="physicalInterfacesLoading"
                  autocomplete="off"
                  style="width: 100%; padding-right: 40px;"
                />
                <button
                  type="button"
                  @click="showSourceIfaceDropdown = !showSourceIfaceDropdown"
                  :disabled="physicalInterfacesLoading"
                  style="position: absolute; right: 5px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; font-size: 18px; color: #666; padding: 0 8px;"
                  title="选择网卡"
                >
                  ▼
                </button>
                <div
                  v-if="showSourceIfaceDropdown"
                  style="position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); z-index: 1000; max-height: 300px; overflow-y: auto; margin-top: 4px;"
                >
                  <div
                    v-for="iface in physicalInterfaces"
                    :key="iface.name"
                    @click="config.source_iface = iface.name; showSourceIfaceDropdown = false"
                    style="padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f0f0;"
                    :style="{ backgroundColor: config.source_iface === iface.name ? '#f0f0f0' : 'white' }"
                    @mouseenter="(e: any) => e.target.style.backgroundColor = '#f8f8f8'"
                    @mouseleave="(e: any) => e.target.style.backgroundColor = config.source_iface === iface.name ? '#f0f0f0' : 'white'"
                  >
                    {{ iface.name }}{{ iface.type === 'wireless' ? ' (无线)' : ' (有线)' }}{{ iface.has_ip && iface.ip ? ' - ' + iface.ip : '' }}
                  </div>
                  <div
                    @click="config.source_iface = ''; showSourceIfaceDropdown = false"
                    style="padding: 10px 12px; cursor: pointer; border-top: 1px solid #ddd; font-weight: 500;"
                    @mouseenter="(e: any) => e.target.style.backgroundColor = '#f8f8f8'"
                    @mouseleave="(e: any) => e.target.style.backgroundColor = 'white'"
                  >
                    自定义...
                  </div>
                </div>
                <datalist id="source-iface-custom-list">
                  <option
                    v-for="iface in physicalInterfaces"
                    :key="iface.name"
                    :value="iface.name"
                  >
                    {{ iface.name }}{{ iface.type === 'wireless' ? ' (无线)' : ' (有线)' }}{{ iface.has_ip && iface.ip ? ' - ' + iface.ip : '' }}
                  </option>
                </datalist>
              </div>
              <span v-if="physicalInterfacesError" class="field-hint" style="color: #ff9800;">{{ physicalInterfacesError }}</span>
              <span v-if="errors.source_iface" class="error-text">{{ errors.source_iface }}</span>
            </div>
            
            <div class="form-group">
              <label for="local_iface">
                本地网络接口
                <span v-if="physicalInterfacesLoading" class="field-hint">(加载中...)</span>
              </label>
              <div class="interface-select-wrapper" style="position: relative;">
                <input
                  id="local_iface"
                  v-model="config.local_iface"
                  type="text"
                  list="local-iface-custom-list"
                  placeholder="输入自定义网卡名称"
                  :class="{ 'error': errors.local_iface }"
                  :disabled="physicalInterfacesLoading"
                  autocomplete="off"
                  style="width: 100%; padding-right: 40px;"
                />
                <button
                  type="button"
                  @click="showLocalIfaceDropdown = !showLocalIfaceDropdown"
                  :disabled="physicalInterfacesLoading"
                  style="position: absolute; right: 5px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; font-size: 18px; color: #666; padding: 0 8px;"
                  title="选择网卡"
                >
                  ▼
                </button>
                <div
                  v-if="showLocalIfaceDropdown"
                  style="position: absolute; top: 100%; left: 0; right: 0; background: white; border: 1px solid #ddd; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); z-index: 1000; max-height: 300px; overflow-y: auto; margin-top: 4px;"
                >
                  <div
                    v-for="iface in physicalInterfaces"
                    :key="iface.name"
                    @click="config.local_iface = iface.name; showLocalIfaceDropdown = false"
                    style="padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f0f0;"
                    :style="{ backgroundColor: config.local_iface === iface.name ? '#f0f0f0' : 'white' }"
                    @mouseenter="(e: any) => e.target.style.backgroundColor = '#f8f8f8'"
                    @mouseleave="(e: any) => e.target.style.backgroundColor = config.local_iface === iface.name ? '#f0f0f0' : 'white'"
                  >
                    {{ iface.name }}{{ iface.type === 'wireless' ? ' (无线)' : ' (有线)' }}{{ iface.has_ip && iface.ip ? ' - ' + iface.ip : '' }}
                  </div>
                  <div
                    @click="config.local_iface = ''; showLocalIfaceDropdown = false"
                    style="padding: 10px 12px; cursor: pointer; border-top: 1px solid #ddd; font-weight: 500;"
                    @mouseenter="(e: any) => e.target.style.backgroundColor = '#f8f8f8'"
                    @mouseleave="(e: any) => e.target.style.backgroundColor = 'white'"
                  >
                    自定义...
                  </div>
                </div>
                <datalist id="local-iface-custom-list">
                  <option
                    v-for="iface in physicalInterfaces"
                    :key="iface.name"
                    :value="iface.name"
                  >
                    {{ iface.name }}{{ iface.type === 'wireless' ? ' (无线)' : ' (有线)' }}{{ iface.has_ip && iface.ip ? ' - ' + iface.ip : '' }}
                  </option>
                </datalist>
              </div>
              <span v-if="physicalInterfacesError" class="field-hint" style="color: #ff9800;">{{ physicalInterfacesError }}</span>
              <span v-if="errors.local_iface" class="error-text">{{ errors.local_iface }}</span>
            </div>
            
            <div class="form-group">
              <label for="output_m3u">
                输出 M3U
              </label>
              <input
                id="output_m3u"
                v-model="config.output_m3u"
                type="text"
                placeholder="例如: /path/to/output.m3u"
                :class="{ 'error': errors.output_m3u }"
              />
              <span v-if="errors.output_m3u" class="error-text">{{ errors.output_m3u }}</span>
            </div>
          </div>
        </div>
        
        <!-- EPG 配置分组 -->
        <div class="config-section">
          <h2 class="section-title collapsible" @click="toggleSection('epg')">
            <span class="section-title-text">EPG 配置</span>
            <span class="collapse-icon" :class="{ 'collapsed': !expandedSections.epg }">▼</span>
          </h2>
          <div v-show="expandedSections.epg" class="section-content">
            <div class="form-group">
              <label for="epg_base_url">
                EPG 查询地址
              </label>
              <input
                id="epg_base_url"
                v-model="config.epg_base_url"
                type="text"
                placeholder="默认值: http://cms.99tv.com.cn:99/cms/liveVideoOtt_searchProgramList6p1.action"
                :class="{ 'error': errors.epg_base_url }"
              />
              <span v-if="errors.epg_base_url" class="error-text">{{ errors.epg_base_url }}</span>
            </div>
            
            <div class="form-group">
              <label for="epg_riddle">
                Riddle
                <span class="field-hint">EPG 请求的 Riddle 参数</span>
              </label>
              <input
                id="epg_riddle"
                v-model="config.epg_riddle"
                type="text"
                placeholder="默认值: 0e5172956bf2c1d87381056eb23ebe5a"
                :class="{ 'error': errors.epg_riddle }"
              />
              <span v-if="errors.epg_riddle" class="error-text">{{ errors.epg_riddle }}</span>
            </div>
            
            <div class="form-group">
              <label for="epg_time_ms">
                Time
                <span class="field-hint">EPG 请求的 Time 参数（时间戳）</span>
              </label>
              <input
                id="epg_time_ms"
                v-model="config.epg_time_ms"
                type="text"
                placeholder="默认值: 1764552092957"
                :class="{ 'error': errors.epg_time_ms }"
              />
              <span v-if="errors.epg_time_ms" class="error-text">{{ errors.epg_time_ms }}</span>
            </div>
            
            <div class="form-group">
              <label for="epg_days_forward">
                向后预告天数
                <span class="field-hint">EPG 数据向后获取的天数（0-30）</span>
              </label>
              <input
                id="epg_days_forward"
                v-model.number="config.epg_days_forward"
                type="number"
                min="0"
                max="30"
                placeholder="默认值: 7"
                :class="{ 'error': errors.epg_days_forward }"
              />
              <span v-if="errors.epg_days_forward" class="error-text">{{ errors.epg_days_forward }}</span>
            </div>
            
            <div class="form-group">
              <label for="epg_days_back">
                向前回看天数
                <span class="field-hint">EPG 数据向前回看的天数（0-7）</span>
              </label>
              <input
                id="epg_days_back"
                v-model.number="config.epg_days_back"
                type="number"
                min="0"
                max="7"
                placeholder="默认值: 0"
                :class="{ 'error': errors.epg_days_back }"
              />
              <span v-if="errors.epg_days_back" class="error-text">{{ errors.epg_days_back }}</span>
            </div>
            
            <div class="form-group">
              <label for="epg_out">
                EPG 文件名称
              </label>
              <input
                id="epg_out"
                v-model="config.epg_out"
                type="text"
                placeholder="默认值: epg.xml"
                :class="{ 'error': errors.epg_out }"
              />
              <span v-if="errors.epg_out" class="error-text">{{ errors.epg_out }}</span>
            </div>
          </div>
        </div>
        
        <!-- UDPXY 配置分组 -->
        <div class="config-section" v-if="config.udpxy">
          <h2 class="section-title collapsible" @click="toggleSection('udpxy')">
            <span class="section-title-text">UDPXY 配置</span>
            <span class="collapse-icon" :class="{ 'collapsed': !expandedSections.udpxy }">▼</span>
          </h2>
          <div v-show="expandedSections.udpxy" class="section-content">
            <div class="form-group">
              <label for="udpxy_port">端口</label>
              <input
                id="udpxy_port"
                v-model.number="config.udpxy!.port"
                type="number"
                min="1"
                max="65535"
                :class="{ 'error': errors['udpxy.port'] }"
                :disabled="udpxyStatus?.running"
              />
              <span v-if="errors['udpxy.port']" class="error-text">{{ errors['udpxy.port'] }}</span>
              <span class="field-hint">UDPXY 服务监听端口</span>
            </div>
            
            <div class="form-group">
              <label for="udpxy_bind_address">
                本地监听
                <span v-if="physicalInterfacesLoading" class="field-hint">(加载中...)</span>
              </label>
              <input
                id="udpxy_bind_address"
                v-model="config.udpxy!.bind_address"
                type="text"
                list="udpxy-bind-address-list"
                :class="{ 'error': errors['udpxy.bind_address'] }"
                placeholder="选择或输入 IP 地址，例如: 0.0.0.0, 192.168.1.1"
                :disabled="udpxyStatus?.running || physicalInterfacesLoading"
                autocomplete="off"
              />
              <datalist id="udpxy-bind-address-list">
                <option value="0.0.0.0">0.0.0.0 (所有网络接口)</option>
                <option
                  v-for="iface in physicalInterfaces"
                  :key="iface.name"
                  :value="iface.ip || ''"
                >
                  {{ iface.name }}{{ iface.type === 'wireless' ? ' (无线)' : ' (有线)' }}{{ iface.has_ip && iface.ip ? ' - ' + iface.ip : '' }}
                </option>
              </datalist>
              <span v-if="physicalInterfacesError" class="field-hint" style="color: #ff9800;">{{ physicalInterfacesError }}</span>
              <span v-if="errors['udpxy.bind_address']" class="error-text">{{ errors['udpxy.bind_address'] }}</span>
              <span class="field-hint">服务绑定的 IP 地址（0.0.0.0 表示所有接口）</span>
            </div>
            
            <div class="form-group">
              <label for="udpxy_max_connections">最大连接数</label>
              <input
                id="udpxy_max_connections"
                v-model.number="config.udpxy!.max_connections"
                type="number"
                min="1"
                max="10000"
                :class="{ 'error': errors['udpxy.max_connections'] }"
                :disabled="udpxyStatus?.running"
              />
              <span v-if="errors['udpxy.max_connections']" class="error-text">{{ errors['udpxy.max_connections'] }}</span>
              <span class="field-hint">允许的最大并发连接数</span>
            </div>
          </div>
        </div>
        
        <!-- 回放配置分组（只读显示） -->
        <div class="config-section" v-if="config.catchup">
          <h2 class="section-title collapsible" @click="toggleSection('catchup')">
            <span class="section-title-text">回放配置</span>
            <span class="collapse-icon" :class="{ 'collapsed': !expandedSections.catchup }">▼</span>
          </h2>
          <div v-show="expandedSections.catchup" class="section-content">
            <div class="form-group">
              <label>回放服务器地址</label>
              <input
                :value="`${config.catchup.target_host}:${config.catchup.target_port}`"
                type="text"
                readonly
                class="readonly-input"
                style="background-color: #f5f5f5; cursor: not-allowed;"
              />
              <span class="field-hint">此配置由系统自动从 M3U 源提取，无需手动配置</span>
            </div>
            
            <div class="form-group" v-if="config.catchup.virtual_domain">
              <label>虚拟域名</label>
              <input
                :value="config.catchup.virtual_domain"
                type="text"
                readonly
                class="readonly-input"
                style="background-color: #f5f5f5; cursor: not-allowed;"
              />
            </div>
          </div>
        </div>
        
        <!-- 定时任务配置分组 -->
        <div class="config-group">
          <h2 class="group-title collapsible" @click="toggleSection('cron')">
            <span class="section-title-text">定时任务配置</span>
            <span class="collapse-icon" :class="{ 'collapsed': !expandedSections.cron }">▼</span>
          </h2>
          <div v-show="expandedSections.cron" class="group-content">
            <div class="form-group">
              <label class="checkbox-label">
                <input
                  v-model="cronConfig.enabled"
                  type="checkbox"
                />
                <span>启用定时任务</span>
              </label>
            </div>
            
            <div v-if="cronConfig.enabled" class="cron-enabled-content">
              <div class="config-options">
                <div class="form-group">
                  <label>模式</label>
                  <select v-model="cronConfig.mode" class="form-select">
                    <option value="interval">间隔执行</option>
                    <option value="cron">Cron 表达式</option>
                  </select>
                </div>
                
                <div v-if="cronConfig.mode === 'interval'" class="interval-config">
                  <div class="form-group">
                    <label>间隔小时数</label>
                    <input
                      v-model.number="cronConfig.interval_hours"
                      type="number"
                      min="1"
                      max="24"
                      class="form-input"
                      placeholder="例如: 6"
                    />
                  </div>
                  <div class="form-group">
                    <label>间隔分钟数（可选）</label>
                    <input
                      v-model.number="cronConfig.interval_minutes"
                      type="number"
                      min="0"
                      max="59"
                      class="form-input"
                      placeholder="例如: 30"
                    />
                  </div>
                </div>
                
                <div v-if="cronConfig.mode === 'cron'" class="cron-config">
                  <div class="form-group">
                    <label>Cron 表达式</label>
                    <input
                      v-model="cronConfig.cron_expr"
                      type="text"
                      class="form-input code"
                      placeholder="例如: 0 */6 * * *"
                    />
                    <span class="field-hint">格式: 分 时 日 月 周</span>
                  </div>
                </div>
              </div>
              
              <div v-if="cronSaveError" class="error-message">
                {{ cronSaveError }}
              </div>
              
              <div class="form-actions-inline">
                <button
                  v-if="cronStatus.enabled"
                  type="button"
                  @click="removeCron"
                  :disabled="cronRemoving"
                  class="remove-btn"
                >
                  {{ cronRemoving ? '移除中...' : '移除任务' }}
                </button>
                <button
                  type="button"
                  @click="saveCron"
                  :disabled="cronSaving"
                  class="submit-btn"
                >
                  {{ cronSaving ? '保存中...' : '保存定时任务' }}
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>
        
        <div class="form-actions">
          <button type="submit" :disabled="saving" class="submit-btn">
            {{ saving ? '保存中...' : '保存配置' }}
          </button>
          <button type="button" @click="resetForm" class="reset-btn">重置</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { configApi } from '../api/config'
import { cronApi } from '../api/cron'
import { interfacesApi } from '../api/interfaces'
import { udpxyApi } from '../api/udpxy'
import type { ConfigResponse, UdpxyStatusResponse } from '../types/api'
import type { CronStatusResponse } from '../types/api'
import type { NetworkInterface } from '../types/api'

const loading = ref(true)
const saving = ref(false)
const error = ref<string | null>(null)
const successMessage = ref<string | null>(null)
const originalConfig = ref<ConfigResponse>({
  input_url: '',
  source_iface: '',
  local_iface: '',
  output_m3u: '',
  epg_base_url: '',
  epg_riddle: '',
  epg_time_ms: '',
  epg_days_forward: undefined,
  epg_days_back: undefined,
  epg_out: '',
})
const config = ref<ConfigResponse>({
  input_url: '',
  source_iface: '',
  local_iface: '',
  output_m3u: '',
  epg_base_url: '',
  epg_riddle: '',
  epg_time_ms: '',
  epg_days_forward: undefined,
  epg_days_back: undefined,
  epg_out: '',
})
const errors = ref<Record<string, string>>({})
const physicalInterfaces = ref<NetworkInterface[]>([])
const physicalInterfacesLoading = ref(false)
const physicalInterfacesError = ref<string | null>(null)

// 用于控制下拉菜单的显示/隐藏
const showSourceIfaceDropdown = ref(false)
const showLocalIfaceDropdown = ref(false)

// 定时任务相关
const cronSaving = ref(false)
const cronRemoving = ref(false)
const cronSaveError = ref<string | null>(null)
const cronStatus = ref<CronStatusResponse>({
  enabled: false,
  cron_expr: null,
  cron_cmd: null,
  next_run_info: null,
})
const cronConfig = ref({
  enabled: false,
  mode: 'interval' as 'interval' | 'cron',
  interval_hours: 6,
  interval_minutes: 0,
  cron_expr: '',
})

// UDPXY 状态
const udpxyStatus = ref<UdpxyStatusResponse | null>(null)

// 折叠/展开状态
const expandedSections = ref({
  basic: true,      // 基础信息配置默认展开
  epg: true,        // EPG 配置默认展开
  udpxy: true,      // UDPXY 配置默认展开
  catchup: true,    // 回放配置默认展开
  cron: true,       // 定时任务配置默认展开
})

const toggleSection = (section: 'basic' | 'epg' | 'udpxy' | 'catchup' | 'cron') => {
  expandedSections.value[section] = !expandedSections.value[section]
}

const validateForm = (): boolean => {
  errors.value = {}
  
  if (!config.value.input_url || !config.value.input_url.trim()) {
    errors.value.input_url = '请输入 IPTV 源地址'
  } else if (!config.value.input_url.startsWith('http://') && !config.value.input_url.startsWith('https://')) {
    errors.value.input_url = 'IPTV 源地址必须以 http:// 或 https:// 开头'
  }
  
  if (!config.value.source_iface || !config.value.source_iface.trim()) {
    errors.value.source_iface = '请输入网卡名称'
  }
  
  if (!config.value.output_m3u || !config.value.output_m3u.trim()) {
    errors.value.output_m3u = '请输入文件名称'
  }
  
  // UDPXY 配置已移除，udpxy_base 自动从 local_iface 获取，无需验证
  
  if (config.value.epg_base_url && config.value.epg_base_url.trim()) {
    if (!config.value.epg_base_url.startsWith('http://') && !config.value.epg_base_url.startsWith('https://')) {
      errors.value.epg_base_url = 'EPG 查询地址必须以 http:// 或 https:// 开头'
    }
  }
  
  if (config.value.epg_days_forward !== undefined && config.value.epg_days_forward !== null) {
    if (config.value.epg_days_forward < 0 || config.value.epg_days_forward > 30) {
      errors.value.epg_days_forward = '向后预告天数必须在 0-30 之间'
    }
  }
  
  if (config.value.epg_days_back !== undefined && config.value.epg_days_back !== null) {
    if (config.value.epg_days_back < 0 || config.value.epg_days_back > 7) {
      errors.value.epg_days_back = '向前回看天数必须在 0-7 之间'
    }
  }
  
  return Object.keys(errors.value).length === 0
}

const loadPhysicalInterfaces = async () => {
  try {
    physicalInterfacesLoading.value = true
    physicalInterfacesError.value = null
    console.log('[Config] 开始加载物理网卡列表...')
    const response = await interfacesApi.getInterfaces(true) // physical=true，只获取物理网卡
    console.log('[Config] API 响应:', response)
    physicalInterfaces.value = response.interfaces || []
    console.log('[Config] 物理网卡列表:', physicalInterfaces.value)
    if (physicalInterfaces.value.length === 0) {
      physicalInterfacesError.value = '未检测到物理网卡，请使用自定义输入'
    }
  } catch (e: any) {
    console.error('[Config] 加载物理网卡列表失败:', e)
    physicalInterfacesError.value = e.message || '加载网卡列表失败，请使用自定义输入'
    // 失败时使用空列表，不影响其他功能
    physicalInterfaces.value = []
  } finally {
    physicalInterfacesLoading.value = false
  }
}

const loadConfig = async () => {
  try {
    loading.value = true
    error.value = null
    successMessage.value = null
    
    // 并行加载配置、定时任务状态、UDPXY 状态和物理网卡列表
    const [loadedConfig, cronData, udpxyStatusData] = await Promise.all([
      configApi.getConfig(),
      cronApi.getStatus().catch(() => ({ enabled: false, cron_expr: null, cron_cmd: null, next_run_info: null })),
      udpxyApi.getStatus().catch(() => null),
    ])
    
    config.value = { ...originalConfig.value, ...loadedConfig } // 合并默认值和加载的配置
    
    // 确保 UDPXY 配置存在，使用 source_iface 的值
    if (!config.value.udpxy) {
      config.value.udpxy = {
        enabled: true,
        port: 4022,
        bind_address: '0.0.0.0',
        source_iface: config.value.source_iface || 'eth1',
        max_connections: 5,
      }
    } else {
      // 同步 source_iface 到 UDPXY 配置
      config.value.udpxy.source_iface = config.value.source_iface || config.value.udpxy.source_iface || 'eth1'
    }
    
    // 加载定时任务状态
    cronStatus.value = cronData
    cronConfig.value.enabled = cronData.enabled
    if (cronData.cron_expr) {
      cronConfig.value.mode = 'cron'
      cronConfig.value.cron_expr = cronData.cron_expr
    } else {
      cronConfig.value.mode = 'interval'
    }
    
    // 加载 UDPXY 状态
    udpxyStatus.value = udpxyStatusData
    
    originalConfig.value = { ...config.value }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  if (!validateForm()) {
    return
  }
  
  try {
    saving.value = true
    error.value = null
    successMessage.value = null
    
    // 保存配置（包括 UDPXY 配置）
    await configApi.updateConfig(config.value)
    successMessage.value = '配置保存成功！'
    
    // 如果 UDPXY 正在运行，需要重启服务以应用新配置
    if (udpxyStatus.value?.running) {
      try {
        await udpxyApi.restart()
        successMessage.value = '配置保存成功！UDPXY 服务已重启'
        // 刷新 UDPXY 状态
        udpxyStatus.value = await udpxyApi.getStatus()
      } catch (e: any) {
        console.error('重启 UDPXY 服务失败:', e)
        // 即使重启失败，也不影响配置保存
      }
    }
    
    originalConfig.value = { ...config.value }
    
    // 3秒后清除成功消息
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (e: any) {
    error.value = e.message || '保存失败'
    successMessage.value = null
  } finally {
    saving.value = false
  }
}

const resetForm = () => {
  config.value = { ...originalConfig.value }
  errors.value = {}
  successMessage.value = null
}

const saveCron = async () => {
  if (!cronConfig.value.enabled) {
    return
  }
  
  try {
    cronSaving.value = true
    cronSaveError.value = null
    
    const config: any = {
      mode: cronConfig.value.mode,
    }
    
    if (cronConfig.value.mode === 'interval') {
      if (cronConfig.value.interval_hours) {
        config.interval_hours = cronConfig.value.interval_hours
      }
      if (cronConfig.value.interval_minutes) {
        config.interval_minutes = cronConfig.value.interval_minutes
      }
    } else {
      if (!cronConfig.value.cron_expr) {
        cronSaveError.value = '请输入 Cron 表达式'
        return
      }
      config.cron_hour = cronConfig.value.cron_expr.split(' ')[1] || '*'
      config.cron_minute = cronConfig.value.cron_expr.split(' ')[0] || '*'
    }
    
    await cronApi.setup(config)
    successMessage.value = '定时任务配置已保存'
    
    // 刷新定时任务状态
    cronStatus.value = await cronApi.getStatus()
    
    // 3秒后清除成功消息
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (e: any) {
    cronSaveError.value = e.message || '保存失败'
  } finally {
    cronSaving.value = false
  }
}

const removeCron = async () => {
  if (!confirm('确定要移除定时任务吗？此操作不可恢复。')) {
    return
  }
  
  try {
    cronRemoving.value = true
    await cronApi.remove()
    successMessage.value = '定时任务已移除'
    cronStatus.value = await cronApi.getStatus()
    cronConfig.value.enabled = false
    setTimeout(() => {
      successMessage.value = null
    }, 2000)
  } catch (e: any) {
    cronSaveError.value = e.message || '移除失败'
  } finally {
    cronRemoving.value = false
  }
}

watch(() => cronConfig.value.enabled, (enabled) => {
  if (!enabled) {
    cronSaveError.value = null
  }
})

// 点击外部区域时关闭下拉菜单
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.interface-select-wrapper')) {
    showSourceIfaceDropdown.value = false
    showLocalIfaceDropdown.value = false
  }
}

onMounted(async () => {
  // 先加载物理网卡列表，然后加载配置
  await loadPhysicalInterfaces()
  await loadConfig()
  // 添加点击外部区域关闭下拉菜单的监听
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  // 移除监听
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.config-page {
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

.config-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #2c3e50;
  font-weight: 500;
  font-size: 14px;
}

.field-hint {
  display: block;
  font-size: 12px;
  color: #7f8c8d;
  font-weight: normal;
  margin-top: 4px;
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
  background-color: #fff;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}

/* 隐藏 datalist 的默认下拉箭头 */
.interface-select-wrapper input[list]::-webkit-calendar-picker-indicator {
  display: none !important;
}

.interface-select-wrapper input[list] {
  -webkit-appearance: none;
  -moz-appearance: textfield;
}

.select-wrapper {
  position: relative;
  width: 100%;
}

.select-wrapper::after {
  content: '';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #555;
  pointer-events: none;
}

.select-wrapper select {
  padding-right: 35px;
}

.custom-input {
  margin-top: 10px;
}

.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group select:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.form-group input[type="text"].error,
.form-group input[type="number"].error,
.form-group select.error {
  border-color: #e74c3c;
}

.error-text {
  display: block;
  color: #e74c3c;
  font-size: 12px;
  margin-top: 4px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  cursor: pointer;
}

.success-message {
  padding: 12px 16px;
  background: #d4edda;
  color: #155724;
  border-radius: 4px;
  border-left: 4px solid #27ae60;
  margin-bottom: 20px;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
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

.reset-btn:hover {
  background: #7f8c8d;
}

.cron-enabled-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 12px;
}

.config-options {
  padding: 16px;
  background: #f8f9fa;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.interval-config,
.cron-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-select,
.form-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.form-input.code {
  font-family: 'Courier New', monospace;
}

.form-actions-inline {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #ecf0f1;
}

.remove-btn {
  padding: 10px 24px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.remove-btn:hover:not(:disabled) {
  background: #c0392b;
}

.remove-btn:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}


.config-section {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #ecf0f1;
}

.config-section:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #3498db;
}

.section-title.collapsible {
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color 0.2s;
  padding: 8px 12px;
  margin-left: -12px;
  margin-right: -12px;
  border-radius: 4px;
}

.section-title.collapsible:hover {
  background-color: #f8f9fa;
}

.section-title-text {
  flex: 1;
}

.collapse-icon {
  font-size: 0.9rem;
  color: #7f8c8d;
  transition: transform 0.3s ease;
  margin-left: 12px;
}

.collapse-icon.collapsed {
  transform: rotate(-90deg);
}

.section-content {
  padding-left: 8px;
}

.config-group {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #ecf0f1;
}

.config-group:last-of-type {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.group-title {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 2px solid #3498db;
}

.group-title.collapsible {
  cursor: pointer;
  user-select: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: background-color 0.2s;
  padding: 8px 12px;
  margin-left: -12px;
  margin-right: -12px;
  border-radius: 4px;
}

.group-title.collapsible:hover {
  background-color: #f8f9fa;
}

.group-content {
  padding-left: 8px;
  margin-top: 16px;
}
</style>

