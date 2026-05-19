import { Card } from '@/components/ui/custom/Card'

interface CourseInsightCardsProps {
  weakestLoCode: string | null
  weakestLoAverageScore: number | null
  mostDifficultAssessmentName: string | null
  mostDifficultAssessmentAverageScore: number | null
  highestVarianceAssessmentName: string | null
  highestVarianceAssessmentSpread: number | null
  studentsBelowThresholdCount: number
  atRiskThreshold: number
}

export const CourseInsightCards = ({
  weakestLoCode,
  weakestLoAverageScore,
  mostDifficultAssessmentName,
  mostDifficultAssessmentAverageScore,
  highestVarianceAssessmentName,
  highestVarianceAssessmentSpread,
  studentsBelowThresholdCount,
  atRiskThreshold,
}: CourseInsightCardsProps) => {
  const cards = [
    {
      label: 'Weakest LO average score',
      value: weakestLoCode ? `${weakestLoCode}: ${weakestLoAverageScore ?? 'N/A'}%` : 'N/A',
      tone: 'text-indigo-700 bg-indigo-50 border-indigo-200',
    },
    {
      label: 'Lowest assessment average score',
      value: mostDifficultAssessmentName ? `${mostDifficultAssessmentName}: ${mostDifficultAssessmentAverageScore ?? 'N/A'}%` : 'N/A',
      tone: 'text-rose-700 bg-rose-50 border-rose-200',
    },
    {
      label: 'Highest assessment score spread',
      value: highestVarianceAssessmentName ? `${highestVarianceAssessmentName}: ${highestVarianceAssessmentSpread ?? 'N/A'} pts` : 'N/A',
      tone: 'text-amber-700 bg-amber-50 border-amber-200',
    },
    {
      label: `Students below ${atRiskThreshold}% course grade`,
      value: String(studentsBelowThresholdCount),
      tone: 'text-violet-700 bg-violet-50 border-violet-200',
    },
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map(card => (
        <Card key={card.label} variant="flat" className={`border ${card.tone}`}>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-80">{card.label}</p>
          <p className="mt-2 text-2xl font-bold">{card.value}</p>
        </Card>
      ))}
    </div>
  )
}
