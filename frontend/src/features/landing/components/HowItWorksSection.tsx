import EmbeddedDemo from './EmbeddedDemo'

const STEPS_DATA = [
  {
    number: '1',
    title: 'Assess',
    description: 'Instructors create assessments aligned to learning outcomes',
    color: 'bg-primary-600',
  },
  {
    number: '2',
    title: 'Map',
    description: 'Scores aggregate into learning outcome achievement levels',
    color: 'bg-violet-600',
  },
  {
    number: '3',
    title: 'Improve',
    description: 'Program outcomes inform curriculum improvements',
    color: 'bg-green-600',
  },
]

const HowItWorksSection = () => {
  return (
    <section id="how-it-works" className="py-20 sm:py-28 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-secondary-900 mb-4">
            See how outcomes flow through your institution
          </h2>
          <p className="text-lg text-secondary-500 max-w-2xl mx-auto">
            From individual assessments to program-level improvement
          </p>
        </div>

        <div className="flex flex-col sm:flex-row justify-center gap-8 sm:gap-16 mb-12">
          {STEPS_DATA.map(({ number, title, description, color }) => (
            <div key={number} className="text-center flex-1 max-w-[200px] mx-auto sm:mx-0">
              <div
                className={`w-10 h-10 ${color} text-white rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-lg`}
              >
                {number}
              </div>
              <h3 className="font-bold text-secondary-900 mb-1">{title}</h3>
              <p className="text-sm text-secondary-500">{description}</p>
            </div>
          ))}
        </div>

        <EmbeddedDemo />
      </div>
    </section>
  )
}

export default HowItWorksSection
