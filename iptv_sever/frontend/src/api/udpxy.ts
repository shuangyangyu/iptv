import api from './index'
import type { UdpxyStatusResponse, UdpxyActionResponse } from '../types/api'

export const udpxyApi = {
  getUdpxyStatus: (): Promise<UdpxyStatusResponse> => {
    return api.get('/udpxy')
  },
  action: (action: 'start' | 'stop' | 'restart'): Promise<UdpxyActionResponse> => {
    return api.post('/udpxy/actions', { action })
  },
  getConfig: (): Promise<any> => {
    return api.get('/udpxy/config')
  },
  updateConfig: (config: any): Promise<any> => {
    return api.put('/udpxy/config', config)
  },
  // 向后兼容的别名
  getStatus: (): Promise<UdpxyStatusResponse> => {
    return api.get('/udpxy')
  },
  start: (): Promise<UdpxyActionResponse> => {
    return api.post('/udpxy/actions', { action: 'start' })
  },
  stop: (): Promise<UdpxyActionResponse> => {
    return api.post('/udpxy/actions', { action: 'stop' })
  },
  restart: (): Promise<UdpxyActionResponse> => {
    return api.post('/udpxy/actions', { action: 'restart' })
  },
}

