export interface GradeItem {
  grade: string
  count: number
  color: string
}

export interface GradeAverageItem {
  averageCourseGrade: number | null
}

export interface LoAverageItem {
  loCode: string
  loDescription?: string
  averageLoScore: number
}

type CourseGradeAverageResponse = {
  weighted_average: number | null
}

type LoAverageResponse = {
  lo_code: string
  lo_description?: string
  avg_score: number
}

export interface CourseInsightSummary {
  courseId: number
  courseCode: string
  courseName: string
  studentCount: number
  averageCourseGrade: number | null
  atRiskStudentCount: number
  atRiskStudentRatio: number
  weakestLoCode: string | null
  weakestLoDescription: string
  weakestLoAverageScore: number | null
}

export const calculateGradeDistribution = (
  courseGradeAverages: GradeAverageItem[]
): GradeItem[] => {
  const validAverages = courseGradeAverages
    .map(g => g.averageCourseGrade)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) {
    return []
  }

  const distribution = {
    A: validAverages.filter(score => score >= 90).length,
    B: validAverages.filter(score => score >= 80 && score < 90).length,
    C: validAverages.filter(score => score >= 70 && score < 80).length,
    D: validAverages.filter(score => score >= 60 && score < 70).length,
    F: validAverages.filter(score => score < 60).length,
  }

  return [
    { grade: 'A', count: distribution.A, color: '#10b981' },
    { grade: 'B', count: distribution.B, color: '#22c55e' },
    { grade: 'C', count: distribution.C, color: '#eab308' },
    { grade: 'D', count: distribution.D, color: '#f97316' },
    { grade: 'F', count: distribution.F, color: '#ef4444' },
  ].filter(item => item.count > 0)
}

export const calculateAverageCourseGrade = (
  courseGradeAverages: GradeAverageItem[]
): number | null => {
  const validAverages = courseGradeAverages
    .map(g => g.averageCourseGrade)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) return null
  const total = validAverages.reduce((sum, score) => sum + score, 0)
  return Math.round(total / validAverages.length)
}

export const countAtRiskStudentsByCourseGrade = (
  courseGradeAverages: GradeAverageItem[],
  threshold = 60,
): number => courseGradeAverages
  .map(g => g.averageCourseGrade)
  .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)
  .filter(averageCourseGrade => averageCourseGrade < threshold).length

export const calculateAtRiskRatioByCourseGrade = (
  courseGradeAverages: GradeAverageItem[],
  threshold = 60,
): number => {
  const validAverages = courseGradeAverages
    .map(g => g.averageCourseGrade)
    .filter((averageCourseGrade): averageCourseGrade is number => averageCourseGrade !== null)

  if (validAverages.length === 0) return 0
  const atRiskCount = validAverages.filter(averageCourseGrade => averageCourseGrade < threshold).length
  return Math.round((atRiskCount / validAverages.length) * 1000) / 10
}

export const findWeakestLoAverageScore = (
  loAverages: LoAverageItem[],
): Pick<CourseInsightSummary, 'weakestLoCode' | 'weakestLoDescription' | 'weakestLoAverageScore'> => {
  if (loAverages.length === 0) {
    return {
      weakestLoCode: null,
      weakestLoDescription: '',
      weakestLoAverageScore: null,
    }
  }

  const weakestLo = [...loAverages].sort((a, b) => a.averageLoScore - b.averageLoScore)[0]
  return {
    weakestLoCode: weakestLo.loCode,
    weakestLoDescription: weakestLo.loDescription ?? '',
    weakestLoAverageScore: Math.round(weakestLo.averageLoScore),
  }
}

export const normalizeCourseGradeAverages = (
  courseGradeAverageResponses: CourseGradeAverageResponse[]
): GradeAverageItem[] => courseGradeAverageResponses.map(courseGradeAverage => ({
  averageCourseGrade: courseGradeAverage.weighted_average,
}))

export const normalizeLoAverages = (
  loAverageResponses: LoAverageResponse[]
): LoAverageItem[] => loAverageResponses.map(loAverage => ({
  loCode: loAverage.lo_code,
  loDescription: loAverage.lo_description,
  averageLoScore: loAverage.avg_score,
}))

export const calculateAverageScore = (
  courseGradeAverages: CourseGradeAverageResponse[]
): number => {
  return calculateAverageCourseGrade(normalizeCourseGradeAverages(courseGradeAverages)) ?? 0
}

export const identifyStudentsAtRisk = (
  courseGradeAverages: CourseGradeAverageResponse[]
): number => countAtRiskStudentsByCourseGrade(normalizeCourseGradeAverages(courseGradeAverages))
