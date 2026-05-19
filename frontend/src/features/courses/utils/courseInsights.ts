interface AssessmentGradeInput {
  score: number
  assessment: {
    total_score?: number | null
    weight?: number | null
  }
}

interface LearningOutcomeInput {
  code: string
}

interface LearningOutcomeScoreInput {
  learning_outcome: {
    code: string
  }
  score?: number | null
}

export const calculateCourseGradeFromAssessmentGrades = (
  grades: AssessmentGradeInput[],
): number | null => {
  if (grades.length === 0) return null

  const assessmentPercentages = grades.map(grade => {
    const totalScore = grade.assessment.total_score ?? 100
    const assessmentScorePercentage = totalScore > 0 ? (grade.score / totalScore) * 100 : 0

    return {
      assessmentScorePercentage,
      weight: grade.assessment.weight ?? 0,
    }
  })

  const weightedAssessments = assessmentPercentages.filter(item => item.weight > 0)

  if (weightedAssessments.length > 0) {
    const totalAvailableWeight = weightedAssessments.reduce((sum, item) => sum + item.weight, 0)
    const weightedCourseGrade = weightedAssessments.reduce(
      (sum, item) => sum + item.assessmentScorePercentage * item.weight,
      0,
    ) / totalAvailableWeight

    return Math.round(weightedCourseGrade * 10) / 10
  }

  const courseGrade = assessmentPercentages.reduce(
    (sum, item) => sum + item.assessmentScorePercentage,
    0,
  ) / assessmentPercentages.length

  return Math.round(courseGrade * 10) / 10
}

export const findWeakestLoAverageScore = (
  learningOutcomes: LearningOutcomeInput[],
  loScores: LearningOutcomeScoreInput[],
): { code: string | null; averageLoScore: number | null } => {
  const rankedLoAverageScores = learningOutcomes
    .map(lo => {
      const matchingScores = loScores.filter(score => score.learning_outcome.code === lo.code)

      if (matchingScores.length === 0) {
        return { code: lo.code, averageLoScore: null }
      }

      const averageLoScore = matchingScores.reduce((sum, score) => sum + (score.score ?? 0), 0) / matchingScores.length
      return {
        code: lo.code,
        averageLoScore: Math.round(averageLoScore * 100) / 100,
      }
    })
    .filter((item): item is { code: string; averageLoScore: number } => item.averageLoScore !== null)
    .sort((a, b) => a.averageLoScore - b.averageLoScore)

  return rankedLoAverageScores[0] ?? { code: null, averageLoScore: null }
}
