import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CourseInsightCards } from './CourseInsightCards'

describe('CourseInsightCards', () => {
  it('shows explicit labels for course detail insight score types', () => {
    render(
      <CourseInsightCards
        weakestLoCode="LO2"
        weakestLoAverageScore={58}
        mostDifficultAssessmentName="Midterm"
        mostDifficultAssessmentAverageScore={62.5}
        highestVarianceAssessmentName="Final"
        highestVarianceAssessmentSpread={41.2}
        studentsBelowThresholdCount={3}
        atRiskThreshold={60}
      />
    )

    expect(screen.getByText('Weakest LO average score')).toBeInTheDocument()
    expect(screen.getByText('LO2: 58%')).toBeInTheDocument()
    expect(screen.getByText('Lowest assessment average score')).toBeInTheDocument()
    expect(screen.getByText('Midterm: 62.5%')).toBeInTheDocument()
    expect(screen.getByText('Highest assessment score spread')).toBeInTheDocument()
    expect(screen.getByText('Final: 41.2 pts')).toBeInTheDocument()
    expect(screen.getByText('Students below 60% course grade')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })
})
