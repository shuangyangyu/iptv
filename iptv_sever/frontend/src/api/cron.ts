import api from './index'
import type { CronStatusResponse } from '../types/api'

export const cronApi = {
  getStatus: (): Promise<CronStatusResponse> => {
    return api.get('/cron')
  },
  setup: (data: {
    mode: 'interval' | 'cron'
    interval_hours?: number
    interval_minutes?: number
    cron_hour?: string
    cron_minute?: string
    source_iface?: string
  }): Promise<any> => {
    return api.post('/cron', data)
  },
  remove: (): Promise<any> => {
    return api.delete('/cron')
  },
}

