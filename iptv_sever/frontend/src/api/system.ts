import api from './index'

export const systemApi = {
  /**
   * 系统健康检查
   * 执行全面的系统环境检测，包括网络、UDPXY、文件系统、配置和服务等各个方面
   */
  healthCheck: (): Promise<any> => {
    return api.post('/system/health-check')
  },
}
