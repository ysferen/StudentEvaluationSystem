import { Link } from 'react-router-dom'

const LoginIllustration = () => {
  return (
    <div className="hidden lg:flex lg:w-1/2 relative bg-secondary-50 overflow-hidden">
      <svg className="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e2e8f0" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />
        <circle cx="20%" cy="30%" r="120" fill="#0d9488" opacity="0.08" />
        <circle cx="80%" cy="70%" r="90" fill="#7c3aed" opacity="0.06" />
        <circle cx="50%" cy="50%" r="60" fill="#0d9488" opacity="0.05" />
      </svg>

      <div className="relative z-10 flex flex-col justify-center px-12 xl:px-20">
        <Link to="/" className="flex items-center gap-3 mb-8">
          <div className="h-10 w-10 bg-primary-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">S</span>
          </div>
          <span className="font-bold text-xl text-secondary-900">SES</span>
        </Link>

        <h2 className="text-3xl xl:text-4xl font-bold text-secondary-900 mb-4 leading-tight">
          Student Evaluation<br />System
        </h2>
        <p className="text-secondary-500 mb-8 max-w-sm leading-relaxed">
          Track achievement from Assessment → Learning Outcome → Program Outcome
        </p>

        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center px-3 py-1.5 bg-primary-100 text-primary-700 text-sm font-medium rounded-full">
            Accreditation-ready
          </span>
          <span className="inline-flex items-center px-3 py-1.5 bg-violet-100 text-violet-700 text-sm font-medium rounded-full">
            Data-driven
          </span>
        </div>
      </div>
    </div>
  )
}

export default LoginIllustration
