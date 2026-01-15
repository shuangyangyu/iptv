import api from './index'
import type { StatusResponse, NetworkInterfacesResponse, NetworkInterfacesDetailResponse, NetworkInterfaceDetailResponse } from '../types/api'

export const statusApi = {
  getStatus: (): Promise<StatusResponse> => {
    return api.get('/status')
  },
  /**
   * 获取网络接口状态详细信息（支持多个接口）
   * @param interfaces 网卡名称，可以是：
   *   - 逗号分隔的多个接口名称（如 "ens160,ens192"）
   *   - 单个接口名称（如 "ens192"）
   *   - "source_iface": 使用配置中的 source_iface
   *   - "local_iface": 使用配置中的 local_iface
   *   - "source_iface,local_iface": 同时使用配置中的 source_iface 和 local_iface
   *   - 不传: 默认同时返回 source_iface 和 local_iface 的信息
   */
  getInterfaceStatus: (interfaces?: string): Promise<NetworkInterfacesDetailResponse> => {
    const params = interfaces !== undefined ? { interfaces } : {}
    return api.get('/status/interfaces', { params })
  },
  // 保持向后兼容的别名（返回第一个接口的信息）
  getNetwork: (interfaces?: string): Promise<NetworkInterfaceDetailResponse> => {
    return statusApi.getInterfaceStatus(interfaces).then(response => {
      // 返回第一个接口的信息以保持向后兼容
      return response.interfaces[0] || {
        name: '',
        ip: null,
        gateway: null,
        has_ip: false,
      }
    })
  },
  /**
   * 获取网络接口列表
   * @param physical 如果为 true，仅返回通过 PIC 识别的真实物理网卡；否则返回所有网卡
   */
  getInterfaces: (physical?: boolean): Promise<NetworkInterfacesResponse> => {
    const params = physical !== undefined ? { physical } : {}
    return api.get('/status/interfaces_list', { params })
  },
}

