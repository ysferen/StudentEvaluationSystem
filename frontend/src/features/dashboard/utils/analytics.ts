export interface GradeItem {
  grade: string
  count: number
  color: string
}

export const calculateGradeDistribution = (
  gradeAverages: Array<{ weighted_average: number | null }>
): GradeItem[] => {
  const validAverages = gradeAverages
    .map(g => g.weighted_average)
    .filter((avg): avg is number => avg !== null)

  if (validAverages.length === 0) {
    return []
  }

  const distribution = {
    A: validAverages.filter(s => s >= 90).length,
    B: validAverages.filter(s => s >= 80 && s < 90).length,
    C: validAverages.filter(s => s >= 70 && s < 80).length,
    D: validAverages.filter(s => s >= 60 && s < 70).length,
    F: validAverages.filter(s => s < 60).length,
  }

  return [
    { grade: 'A', count: distribution.A, color: '#10b981' },
    { grade: 'B', count: distribution.B, color: '#22c55e' },
    { grade: 'C', count: distribution.C, color: '#eab308' },
    { grade: 'D', count: distribution.D, color: '#f97316' },
    { grade: 'F', count: distribution.F, color: '#ef4444' },
  ].filter(item => item.count > 0)
}

export const calculateAverageScore = (
  gradeAverages: Array<{ weighted_average: number | null }>
): number => {
  const validAverages = gradeAverages
    .map(g => g.weighted_average)
    .filter((avg): avg is number => avg !== null)

  if (validAverages.length === 0) return 0
  const total = validAverages.reduce((sum, score) => sum + score, 0)
  return Math.round(total / validAverages.length)
}

export const identifyStudentsAtRisk = (
  gradeAverages: Array<{ weighted_average: number | null }>
): number => {
  const validAverages = gradeAverages
    .map(g => g.weighted_average)
    .filter((avg): avg is number => avg !== null)

  return validAverages.filter(average => average < 60).length
}
