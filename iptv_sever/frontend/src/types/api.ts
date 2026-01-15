// API 类型定义

export interface FileStatus {
  exists: boolean
  size: number
  mtime: number
  download_url?: string | null
}

export interface StatusResponse {
  m3u: FileStatus
  epg: FileStatus
  last_job?: string | null
  last_job_rc?: number | null
  last_job_at?: number | null
  udpxy?: UdpxyStatusResponse | null
}

export interface ConfigResponse {
  input_url: string
  source_iface: string
  local_iface?: string | null
  output_m3u: string
  use_udpxy?: boolean
  udpxy_base?: string | null
  x_tvg_url?: string | null
  timeout_s?: number
  user_agent?: string
  download_logos?: boolean
  localize_logos?: boolean
  logo_skip_existing?: boolean
  logo_dir?: string
  epg_base_url?: string
  epg_riddle?: string
  epg_time_ms?: string
  epg_days_forward?: number
  epg_days_back?: number
  epg_out?: string
  scheduler_mode?: string
  scheduler_interval_hours?: number
  scheduler_interval_minutes?: number
  scheduler_cron_hour?: string
  scheduler_cron_minute?: string
  udpxy?: {
    enabled: boolean
    port: number
    bind_address: string
    source_iface: string
    max_connections: number
    log_file?: string | null
    pid_file?: string | null
  } | null
  catchup?: CatchupConfigResponse | null
  [key: string]: any
}

export interface NetworkResponse {
  interface: string
  ip?: string | null
  gateway?: string | null
}

export interface LogEntry {
  ts: number
  level: string
  msg: string
}

export interface LogsResponse {
  logs: LogEntry[]
}

export interface CronStatusResponse {
  enabled: boolean
  cron_expr?: string | null
  cron_cmd?: string | null
  next_run_info?: string | null
}

export interface UdpxyStatusResponse {
  running: boolean
  pid?: number | null
  port: number
  bind_address: string
  source_iface: string
  max_connections: number
  connections: number
  uptime: number
  available: boolean
}

export interface UdpxyActionResponse {
  ok: boolean
  message: string
  running: boolean
  pid: number | null
}

export interface CatchupConfigResponse {
  target_host: string
  target_port: number
  virtual_domain?: string | null
}

export interface NetworkInterface {
  name: string
  status?: 'up' | 'down' | 'unknown' | null
  ip?: string | null
  has_ip: boolean
  // 物理网卡特有字段
  pic_id?: string | null
  mac_address?: string | null
  type?: 'ethernet' | 'wireless' | null
  driver?: string | null
  speed?: string | null
  duplex?: string | null
}

export interface NetworkInterfacesResponse {
  interfaces: NetworkInterface[]
  physical_only: boolean
}

export interface NetworkInterfaceDetailResponse {
  name: string
  ip?: string | null
  gateway?: string | null
  has_ip: boolean
}

export interface NetworkInterfacesDetailResponse {
  interfaces: NetworkInterfaceDetailResponse[]
}
