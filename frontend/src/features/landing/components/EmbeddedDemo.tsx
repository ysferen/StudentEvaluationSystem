import { useState } from 'react'

type DemoStep = 'assessment' | 'lo' | 'po'

const STEPS: { key: DemoStep; label: string; color: string }[] = [
  { key: 'assessment', label: 'Midterm Exam', color: 'primary' },
  { key: 'lo', label: 'LO 3.2', color: 'violet' },
  { key: 'po', label: 'PO 1', color: 'green' },
]

const ASSESSMENT_DATA = [
  { student: 'Ahmet Y.', score: 85, status: 'Complete' },
  { student: 'Elif K.', score: 72, status: 'Complete' },
  { student: 'Mehmet A.', score: 91, status: 'Complete' },
  { student: 'Zeynep D.', score: 68, status: 'Complete' },
]

const LO_DATA = { name: 'LO 3.2', description: 'Apply statistical methods to engineering problems', average: '79%', target: '70%', status: 'Met' }

const PO_DATA = { name: 'PO 1', description: 'Engineering knowledge and problem analysis', mappedLOs: 4, averageScore: '76%', status: 'On Track' }

const colorMap: Record<string, { bg: string; text: string; badge: string; bar: string }> = {
  primary: { bg: 'bg-primary-50', text: 'text-primary-700', badge: 'bg-primary-100 text-primary-700', bar: 'bg-primary-500' },
  violet: { bg: 'bg-violet-50', text: 'text-violet-700', badge: 'bg-violet-100 text-violet-700', bar: 'bg-violet-500' },
  green: { bg: 'bg-green-50', text: 'text-green-700', badge: 'bg-green-100 text-green-700', bar: 'bg-green-500' },
}

const EmbeddedDemo = () => {
  const [activeStep, setActiveStep] = useState<DemoStep>('assessment')

  return (
    <div className="bg-secondary-50 rounded-xl border border-secondary-200 overflow-hidden">
      <div className="px-4 py-2 text-xs text-secondary-400 text-center border-b border-secondary-200">
        ← Interactive demo — click through the flow →
      </div>

      <div className="flex items-center justify-center gap-2 sm:gap-3 px-4 py-3 bg-white border-b border-secondary-200">
        {STEPS.map((step, i) => (
          <button
            key={step.key}
            onClick={() => setActiveStep(step.key)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs sm:text-sm font-semibold transition-colors ${
              activeStep === step.key
                ? `${colorMap[step.color].badge}`
                : 'text-secondary-400 hover:text-secondary-600'
            }`}
          >
            <span className="w-5 h-5 rounded-full bg-current/[0.15] flex items-center justify-center text-[10px]">
              {i + 1}
            </span>
            {step.label}
            {i < STEPS.length - 1 && <span className="text-secondary-300 mx-1">→</span>}
          </button>
        ))}
      </div>

      <div className="p-4 sm:p-6">
        {activeStep === 'assessment' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.primary.text}`}>Midterm Exam</span>
              <span className="text-xs bg-primary-100 text-primary-700 px-2 py-0.5 rounded-full font-medium">Assessment</span>
            </div>
            <div className="space-y-2">
              {ASSESSMENT_DATA.map((row) => (
                <div key={row.student} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-secondary-200">
                  <span className="text-xs sm:text-sm text-secondary-700">{row.student}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs sm:text-sm font-semibold text-secondary-900">{row.score}</span>
                    <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded">{row.status}</span>
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Individual scores are collected and mapped…</p>
          </div>
        )}

        {activeStep === 'lo' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.violet.text}`}>{LO_DATA.name}</span>
              <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">Learning Outcome</span>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 p-3 sm:p-4 space-y-2">
              <p className="text-xs sm:text-sm text-secondary-600">{LO_DATA.description}</p>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-violet-700">{LO_DATA.average}</div>
                  <div className="text-[10px] text-secondary-500">Average</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-secondary-900">{LO_DATA.target}</div>
                  <div className="text-[10px] text-secondary-500">Target</div>
                </div>
                <div className="text-center">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">{LO_DATA.status}</span>
                </div>
              </div>
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Aggregated into program-level outcomes…</p>
          </div>
        )}

        {activeStep === 'po' && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className={`text-sm font-bold ${colorMap.green.text}`}>{PO_DATA.name}</span>
              <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">Program Outcome</span>
            </div>
            <div className="bg-white rounded-lg border border-secondary-200 p-3 sm:p-4 space-y-2">
              <p className="text-xs sm:text-sm text-secondary-600">{PO_DATA.description}</p>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-700">{PO_DATA.mappedLOs}</div>
                  <div className="text-[10px] text-secondary-500">Mapped LOs</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-secondary-900">{PO_DATA.averageScore}</div>
                  <div className="text-[10px] text-secondary-500">Average</div>
                </div>
                <div className="text-center">
                  <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">{PO_DATA.status}</span>
                </div>
              </div>
            </div>
            <p className="text-xs text-secondary-400 mt-3 text-center">Data informs curriculum improvements → cycle repeats</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default EmbeddedDemo
