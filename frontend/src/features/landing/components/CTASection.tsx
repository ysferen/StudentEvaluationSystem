import { Link } from 'react-router-dom'

const CTASection = () => {
  return (
    <section className="bg-primary-600 py-20 sm:py-24">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
          Ready to improve your program outcomes?
        </h2>
        <p className="text-lg text-primary-100 mb-8 max-w-2xl mx-auto">
          Join your institution's evaluation system and start making data-informed decisions.
        </p>
        <Link
          to="/login"
          className="inline-block px-8 py-3.5 bg-white text-primary-600 font-bold rounded-xl shadow-lg hover:bg-primary-50 transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5"
        >
          Get Started
        </Link>
      </div>
    </section>
  )
}

export default CTASection
