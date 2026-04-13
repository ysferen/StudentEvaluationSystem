import { useQuery } from '@tanstack/react-query'
import { axiosInstance } from '../../../shared/api/mutator'

interface Stats {
  universities: number
  departments: number
  programs: number
  courses: number
}

export const useLandingStats = () => {
  return useQuery<Stats>({
    queryKey: ['landing-stats'],
    queryFn: async () => {
      const [universities, departments, programs, courses] = await Promise.all([
        axiosInstance.get('/api/core/universities/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/departments/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/programs/', { params: { page_size: 1 } }).then((r) => r.data),
        axiosInstance.get('/api/core/courses/', { params: { page_size: 1 } }).then((r) => r.data),
      ])

      return {
        universities: universities.count ?? 0,
        departments: departments.count ?? 0,
        programs: programs.count ?? 0,
        courses: courses.count ?? 0,
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}
