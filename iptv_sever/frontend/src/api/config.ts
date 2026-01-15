import api from './index'
import type { ConfigResponse } from '../types/api'

export const configApi = {
  getConfig: (): Promise<ConfigResponse> => {
    return api.get('/config')
  },
  updateConfig: (config: Partial<ConfigResponse>): Promise<{ ok: boolean; config: ConfigResponse }> => {
    return api.put('/config', config)
  },
}

