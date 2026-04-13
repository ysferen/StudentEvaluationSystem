import { Link } from 'react-router-dom'

const Footer = () => {
  return (
    <footer className="bg-secondary-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="flex flex-col md:flex-row justify-between gap-8 mb-8">
          <div className="max-w-sm">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-7 w-7 bg-primary-600 rounded-md flex items-center justify-center">
                <span className="text-white font-bold text-xs">S</span>
              </div>
              <span className="font-bold text-base">Student Evaluation System</span>
            </div>
            <p className="text-secondary-400 text-sm leading-relaxed">
              Outcome-based assessment platform for higher education. Track achievement, improve teaching, meet accreditation standards.
            </p>
          </div>

          <div className="flex gap-16">
            <div>
              <h4 className="font-semibold text-sm text-secondary-200 mb-3">Platform</h4>
              <ul className="space-y-2">
                <li><a href="#features" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Features</a></li>
                <li><a href="#how-it-works" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">How It Works</a></li>
                <li><a href="#roles" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Roles</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-sm text-secondary-200 mb-3">University</h4>
              <ul className="space-y-2">
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Universities</Link></li>
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Departments</Link></li>
                <li><Link to="/login" className="text-secondary-400 text-sm hover:text-primary-400 transition-colors">Programs</Link></li>
              </ul>
            </div>
          </div>
        </div>

        <div className="border-t border-secondary-700 pt-6 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-secondary-500 text-xs">&copy; 2026 Student Evaluation System</p>
          <div className="flex gap-6">
            <span className="text-secondary-500 text-xs hover:text-secondary-300 cursor-pointer">Privacy</span>
            <span className="text-secondary-500 text-xs hover:text-secondary-300 cursor-pointer">Terms</span>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer
