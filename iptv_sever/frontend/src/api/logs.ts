import api from './index'
import type { LogsResponse } from '../types/api'

export const logsApi = {
  getLogs: (limit: number = 200): Promise<LogsResponse> => {
    return api.get('/logs', { params: { limit } })
  },
  clearLogs: (): Promise<{ ok: boolean }> => {
    return api.post('/logs/clear')
  },
}

