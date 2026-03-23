'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const { user, logout } = useAuth()
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  const navItems = [
    { name: 'Dashboard', href: '/simple-dashboard' },
    { name: 'Workflow Chat', href: '/workflow-chat' },
    { name: 'Documents', href: '/documents-integrated' },
    { name: 'Dynamic Analytics', href: '/data-analysis' },
    { name: 'Cost Estimation', href: '/cost-estimation' },
    { name: 'Intent Demo', href: '/intent-demo' },
  ]

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-14">
          <div className="flex items-center min-w-0">
            <div className="flex-shrink-0">
              <Link href="/overview" className="text-lg font-bold text-blue-600 whitespace-nowrap">
                Industry AI Flow
              </Link>
            </div>

            <div className="hidden lg:ml-6 lg:flex lg:items-center lg:space-x-1">
              {navItems.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`px-2.5 py-1.5 text-sm font-medium rounded-md transition whitespace-nowrap ${
                    pathname === item.href
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                >
                  {item.name}
                </Link>
              ))}
            </div>
          </div>

          <div className="flex items-center flex-shrink-0 ml-4">
            {user ? (
              <div className="flex items-center space-x-3">
                <span className="hidden xl:inline text-gray-500 text-sm truncate max-w-[180px]">
                  {user.name}
                </span>
                <button
                  onClick={handleLogout}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg text-sm font-medium transition whitespace-nowrap"
                >
                  Log out
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  href="/login"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition"
                >
                  Log in
                </Link>
              </div>
            )}

            {/* Mobile menu button */}
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="lg:hidden ml-3 inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-blue-600 hover:bg-gray-100"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                {isMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        {isMenuOpen && (
          <div className="lg:hidden border-t border-gray-200">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navItems.map((item) => (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`block px-3 py-2 text-base font-medium rounded-md ${
                    pathname === item.href
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-700 hover:text-blue-600 hover:bg-gray-50'
                  }`}
                  onClick={() => setIsMenuOpen(false)}
                >
                  {item.name}
                </Link>
              ))}

              {user && (
                <>
                  <div className="px-3 py-2 text-sm text-gray-500 border-t border-gray-200 mt-2 pt-2">
                    {user.name} ({user.email})
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left text-gray-700 hover:text-blue-600 block px-3 py-2 text-base font-medium"
                  >
                    Log out
                  </button>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}
