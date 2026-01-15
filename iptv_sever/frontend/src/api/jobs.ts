import api from './index'

export const jobsApi = {
  runJob: (jobType: 'm3u' | 'epg' | 'logos'): Promise<any> => {
    return api.post(`/jobs/${jobType}`)
  },
}

