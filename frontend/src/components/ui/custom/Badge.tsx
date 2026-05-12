import React from 'react'
import clsx from 'clsx'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'
    size?: 'sm' | 'md'
    rounded?: boolean
}

export const Badge = ({
    children,
    className,
    variant = 'primary',
    size = 'sm',
    rounded = true,
    ...props
}: BadgeProps) => {
    const variants = {
        primary: 'bg-primary-100 text-primary-800',
        secondary: 'bg-secondary-100 text-secondary-800',
        success: 'bg-success-100 text-success-800',
        warning: 'bg-warning-100 text-warning-800',
        danger: 'bg-danger-100 text-danger-800',
        info: 'bg-blue-100 text-blue-800'
    }

    const sizes = {
        sm: 'px-2.5 py-0.5 text-xs',
        md: 'px-3 py-1 text-sm'
    }

    return (
        <span
            className={clsx(
                'inline-flex items-center font-medium',
                rounded ? 'rounded-full' : 'rounded',
                variants[variant],
                sizes[size],
                className
            )}
            {...props}
        >
            {children}
        </span>
    )
}
