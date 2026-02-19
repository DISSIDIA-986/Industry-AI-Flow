'use client'

import { ReactNode } from 'react'

interface FormProps {
  children: ReactNode
  onSubmit?: (e: React.FormEvent) => void
  className?: string
}

export function Form({ children, onSubmit, className = '' }: FormProps) {
  return (
    <form onSubmit={onSubmit} className={`space-y-6 ${className}`}>
      {children}
    </form>
  )
}

interface FormGroupProps {
  children: ReactNode
  label?: string
  error?: string
  helpText?: string
  required?: boolean
  className?: string
}

export function FormGroup({ 
  children, 
  label, 
  error, 
  helpText, 
  required = false,
  className = '' 
}: FormGroupProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {children}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {helpText && !error && <p className="text-sm text-gray-500">{helpText}</p>}
    </div>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string
}

export function Input({ error, className = '', ...props }: InputProps) {
  return (
    <input
      className={`
        w-full px-3 py-2 border rounded-lg shadow-sm
        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
        ${error ? 'border-red-300' : 'border-gray-300'}
        ${className}
      `}
      {...props}
    />
  )
}

interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: string
}

export function TextArea({ error, className = '', ...props }: TextAreaProps) {
  return (
    <textarea
      className={`
        w-full px-3 py-2 border rounded-lg shadow-sm
        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
        ${error ? 'border-red-300' : 'border-gray-300'}
        ${className}
      `}
      {...props}
    />
  )
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  error?: string
  options: { value: string; label: string }[]
}

export function Select({ error, options, className = '', ...props }: SelectProps) {
  return (
    <select
      className={`
        w-full px-3 py-2 border rounded-lg shadow-sm
        focus:ring-2 focus:ring-blue-500 focus:border-blue-500
        ${error ? 'border-red-300' : 'border-gray-300'}
        ${className}
      `}
      {...props}
    >
      <option value="">请选择...</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function Checkbox({ label, error, className = '', ...props }: CheckboxProps) {
  return (
    <div className="space-y-2">
      <label className="flex items-center space-x-3">
        <input
          type="checkbox"
          className={`
            h-4 w-4 text-blue-600 rounded
            focus:ring-blue-500 border-gray-300
            ${error ? 'border-red-300' : ''}
            ${className}
          `}
          {...props}
        />
        <span className="text-sm text-gray-700">{label}</span>
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}

interface RadioGroupProps {
  label?: string
  error?: string
  options: { value: string; label: string }[]
  value: string
  onChange: (value: string) => void
  className?: string
}

export function RadioGroup({ 
  label, 
  error, 
  options, 
  value, 
  onChange,
  className = '' 
}: RadioGroupProps) {
  return (
    <div className={`space-y-3 ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-700">
          {label}
        </label>
      )}
      <div className="space-y-2">
        {options.map((option) => (
          <label key={option.value} className="flex items-center space-x-3">
            <input
              type="radio"
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
            />
            <span className="text-sm text-gray-700">{option.label}</span>
          </label>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  )
}

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

export function Button({ 
  children, 
  variant = 'primary', 
  size = 'md',
  loading = false,
  disabled,
  className = '',
  ...props 
}: ButtonProps) {
  const variantClasses = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800',
    danger: 'bg-red-600 hover:bg-red-700 text-white',
    outline: 'bg-white border border-gray-300 hover:bg-gray-50 text-gray-700'
  }

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base'
  }

  return (
    <button
      className={`
        rounded-lg font-medium transition
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${className}
      `}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <div className="flex items-center justify-center space-x-2">
          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span>处理中...</span>
        </div>
      ) : (
        children
      )}
    </button>
  )
}

export default {
  Form,
  FormGroup,
  Input,
  TextArea,
  Select,
  Checkbox,
  RadioGroup,
  Button
}