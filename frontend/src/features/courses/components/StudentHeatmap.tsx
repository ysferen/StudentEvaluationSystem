import React from 'react'

export interface HeatmapData {
  studentName: string
  studentId: number
  loScores: Record<string, number>
}

interface StudentHeatmapProps {
  loCodes: string[]
  students: HeatmapData[]
  onStudentClick?: (studentName: string) => void
}

const getHeatmapColor = (score: number): string => {
  if (score === 0) return 'rgb(249, 250, 251)'
  const normalized = Math.max(0, Math.min(100, score)) / 100

  if (normalized < 0.25) {
    const t = normalized / 0.25
    const r = 239 - Math.round(11 * t)
    const g = 68 + Math.round(46 * t)
    const b = 68 + Math.round(14 * t)
    return `rgb(${r}, ${g}, ${b})`
  } else if (normalized < 0.5) {
    const t = (normalized - 0.25) / 0.25
    const r = 228 + Math.round(24 * t)
    const g = 114 + Math.round(97 * t)
    const b = 82 - Math.round(27 * t)
    return `rgb(${r}, ${g}, ${b})`
  } else if (normalized < 0.75) {
    const t = (normalized - 0.5) / 0.25
    const r = 252 - Math.round(68 * t)
    const g = 211 + Math.round(33 * t)
    const b = 55 + Math.round(58 * t)
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = (normalized - 0.75) / 0.25
    const r = 184 - Math.round(150 * t)
    const g = 244 - Math.round(42 * t)
    const b = 113 + Math.round(19 * t)
    return `rgb(${r}, ${g}, ${b})`
  }
}

const getTextColor = (score: number): string => {
  if (score === 0) return 'rgb(107, 114, 128)'
  if (score >= 60) return 'rgb(17, 24, 39)'
  return 'rgb(255, 255, 255)'
}

export const StudentHeatmap: React.FC<StudentHeatmapProps> = ({
  loCodes,
  students,
  onStudentClick,
}) => {
  if (students.length === 0) return null

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-secondary-100">
              <th className="sticky left-0 bg-secondary-100 px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-r border-secondary-200 z-10 min-w-[120px] max-w-[180px]">
                Student
              </th>
              {loCodes.map((loCode) => (
                <th key={loCode} className="px-2 py-1.5 text-center text-xs font-semibold text-secondary-700 border-b border-secondary-200 min-w-[60px]">
                  {loCode}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((student, idx) => (
              <tr
                key={student.studentId}
                className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                onClick={() => onStudentClick?.(student.studentName)}
              >
                <td className="sticky left-0 px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-r border-secondary-200 truncate min-w-[120px] max-w-[180px]" style={{ backgroundColor: idx % 2 === 0 ? '#fff' : '#f9fafbfa' }}>
                  {student.studentName}
                </td>
                {loCodes.map((loCode) => {
                  const score = student.loScores[loCode]
                  const displayScore = score ?? 0
                  const bgColor = getHeatmapColor(displayScore)
                  const textColor = getTextColor(displayScore)
                  return (
                    <td
                      key={loCode}
                      className="px-2 py-1.5 text-center text-xs font-medium border-b border-secondary-200"
                      style={{ backgroundColor: bgColor, color: textColor }}
                    >
                      {score != null ? score.toFixed(1) : '\u2212'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-center gap-1">
        {[0, 25, 50, 75, 100].map((val) => (
          <div key={val} className="flex items-center gap-1">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
            <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
          </div>
        ))}
      </div>
    </>
  )
}

interface AssessmentCell {
  id: number
  name: string
  totalScore: number
}

interface AssessmentStudent {
  name: string
  scores: Record<number, number>
}

interface AssessmentHeatmapProps {
  assessments: AssessmentCell[]
  students: AssessmentStudent[]
  onStudentClick?: (studentName: string) => void
}

export const AssessmentHeatmap: React.FC<AssessmentHeatmapProps> = ({
  assessments,
  students,
  onStudentClick,
}) => {
  if (students.length === 0) return null

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-secondary-100">
              <th className="sticky left-0 bg-secondary-100 px-2 py-1.5 text-left text-xs font-semibold text-secondary-700 border-b border-r border-secondary-200 z-10 min-w-[120px] max-w-[180px]">
                Student
              </th>
              {assessments.map((a) => (
                <th key={a.id} className="px-2 py-1.5 text-center text-xs font-semibold text-secondary-700 border-b border-secondary-200 min-w-[60px]">
                  <div className="truncate max-w-[80px]" title={a.name}>{a.name}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {students.map((student, idx) => (
              <tr
                key={idx}
                className={`cursor-pointer hover:bg-secondary-100/50 ${idx % 2 === 0 ? 'bg-white' : 'bg-secondary-50/50'}`}
                onClick={() => onStudentClick?.(student.name)}
              >
                <td className="sticky left-0 px-2 py-1.5 text-sm font-medium text-secondary-900 border-b border-r border-secondary-200 truncate min-w-[120px] max-w-[180px]" style={{ backgroundColor: idx % 2 === 0 ? '#fff' : '#f9fafbfa' }}>
                  {student.name}
                </td>
                {assessments.map((a) => {
                  const pct = student.scores[a.id]
                  const displayPct = pct ?? 0
                  const bgColor = getHeatmapColor(displayPct)
                  const textColor = getTextColor(displayPct)
                  return (
                    <td
                      key={a.id}
                      className="px-2 py-1.5 text-center text-xs font-medium border-b border-secondary-200"
                      style={{ backgroundColor: bgColor, color: textColor }}
                    >
                      {pct != null ? pct.toFixed(1) : '\u2212'}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-center gap-1">
        {[0, 25, 50, 75, 100].map((val) => (
          <div key={val} className="flex items-center gap-1">
            <div className="w-4 h-4 rounded" style={{ backgroundColor: getHeatmapColor(val) }} />
            <span className="text-xs text-secondary-600 tabular-nums">{val}%</span>
          </div>
        ))}
      </div>
    </>
  )
}
