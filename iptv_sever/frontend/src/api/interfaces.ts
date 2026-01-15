import api from './index'
import type { NetworkInterfacesResponse, NetworkInterfacesDetailResponse } from '../types/api'

export const interfacesApi = {
  /**
   * 获取网络接口列表
   * @param physical 如果为 true，仅返回通过 PIC 识别的真实物理网卡；否则返回所有网卡
   */
  getInterfaces: (physical?: boolean): Promise<NetworkInterfacesResponse> => {
    const params = physical !== undefined ? { physical } : {}
    return api.get('/interfaces', { params })
  },
  /**
   * 获取网络接口状态详细信息（支持多个接口）
   * @param name 网卡名称或特殊标识符，可以是：
   *   - 接口名称（如 "ens192"）
   *   - "source_iface": 使用配置中的 source_iface
   *   - "local_iface": 使用配置中的 local_iface
   *   - 逗号分隔的多个接口名称（如 "ens160,ens192"）
   *   - "source_iface,local_iface": 同时使用配置中的 source_iface 和 local_iface
   */
  getInterfaceStatus: (name: string): Promise<NetworkInterfacesDetailResponse> => {
    return api.get(`/interfaces/${name}`)
  },
}
