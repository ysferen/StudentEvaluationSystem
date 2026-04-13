import { Link } from 'react-router-dom'

const HeroSection = () => {
  return (
    <section className="relative bg-secondary-900 overflow-hidden">
      <div className="absolute inset-0 opacity-5">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage:
              'radial-gradient(circle at 25% 25%, rgba(13,148,136,0.3) 0%, transparent 50%), radial-gradient(circle at 75% 75%, rgba(124,58,237,0.2) 0%, transparent 50%)',
          }}
        />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-32 pb-20 sm:pt-40 sm:pb-28">
        <div className="text-center">
          <div className="inline-flex items-center px-4 py-1.5 bg-primary-100 text-primary-700 rounded-full text-sm font-semibold mb-6">
            Outcome-Based Assessment Platform
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight mb-6">
            Drive Continuous Improvement{' '}
            <span className="text-primary-400">in Education</span>
          </h1>

          <p className="max-w-2xl mx-auto text-lg sm:text-xl text-secondary-300 mb-10 leading-relaxed">
            Track student achievement from Assessment → Learning Outcome → Program
            Outcome. Make data-driven decisions that improve teaching quality and program
            accreditation.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              to="/login"
              className="px-8 py-3.5 bg-primary-600 text-white font-semibold rounded-xl shadow-lg hover:bg-primary-700 transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5"
            >
              Get Started
            </Link>
            <a
              href="#how-it-works"
              className="px-8 py-3.5 bg-white/10 text-white font-semibold rounded-xl border border-white/20 hover:bg-white/20 transition-all duration-200"
            >
              See How It Works
            </a>
          </div>

          <div className="max-w-3xl mx-auto">
            <div className="bg-white rounded-xl shadow-2xl overflow-hidden border border-secondary-200">
              <div className="bg-secondary-100 px-4 py-2.5 flex items-center gap-2 border-b border-secondary-200">
                <div className="w-3 h-3 rounded-full bg-red-400" />
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <div className="w-3 h-3 rounded-full bg-green-400" />
                <div className="flex-1 mx-4">
                  <div className="bg-white rounded-md px-3 py-1 text-xs text-secondary-400 text-center max-w-xs mx-auto">
                    ses.example.edu
                  </div>
                </div>
              </div>
              <div className="p-4 sm:p-6 bg-secondary-50">
                <div className="flex gap-4 sm:gap-6">
                  <div className="hidden sm:block w-36 bg-white rounded-lg border border-secondary-200 p-3 space-y-2">
                    <div className="text-primary-600 font-semibold text-xs">Navigation</div>
                    <div className="h-2 bg-secondary-200 rounded w-full" />
                    <div className="h-2 bg-secondary-200 rounded w-3/4" />
                    <div className="h-2 bg-secondary-200 rounded w-5/6" />
                  </div>
                  <div className="flex-1 space-y-3 sm:space-y-4">
                    <div className="font-semibold text-secondary-900 text-sm">
                      Course Outcomes Overview
                    </div>
                    <div className="grid grid-cols-3 gap-2 sm:gap-3">
                      <div className="bg-green-50 border border-green-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-green-700 font-bold text-lg sm:text-xl">87%</div>
                        <div className="text-secondary-500 text-xs">LO Avg</div>
                      </div>
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-amber-700 font-bold text-lg sm:text-xl">72%</div>
                        <div className="text-secondary-500 text-xs">PO Avg</div>
                      </div>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 sm:p-3 text-center">
                        <div className="text-blue-700 font-bold text-lg sm:text-xl">24</div>
                        <div className="text-secondary-500 text-xs">Students</div>
                      </div>
                    </div>
                    <div className="bg-white rounded-lg border border-secondary-200 p-3 flex items-end gap-1 h-16">
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '60%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '80%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '45%' }} />
                      <div className="flex-1 bg-primary-600 rounded-sm" style={{ height: '90%' }} />
                      <div className="flex-1 bg-primary-500 rounded-sm" style={{ height: '70%' }} />
                      <div className="flex-1 bg-primary-400 rounded-sm" style={{ height: '55%' }} />
                      <div className="flex-1 bg-primary-300 rounded-sm" style={{ height: '40%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default HeroSection
