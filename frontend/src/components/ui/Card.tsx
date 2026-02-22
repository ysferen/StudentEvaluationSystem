import React from 'react'
import clsx from 'clsx'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'hover' | 'glass' | 'flat'
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

export const Card = ({
  children,
  className,
  variant = 'default',
  padding = 'md',
  ...props
}: CardProps) => {
  const variants = {
    default: 'bg-white shadow-card border border-secondary-200',
    hover: 'bg-white shadow-card border border-secondary-200 transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5',
    glass: 'bg-white/70 backdrop-blur-lg border border-white/20 shadow-lg',
    flat: 'bg-white border border-secondary-200'
  }

  const paddings = {
    none: '',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8'
  }

  return (
    <div
      className={clsx(
        'rounded-xl',
        variants[variant],
        paddings[padding],
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}
