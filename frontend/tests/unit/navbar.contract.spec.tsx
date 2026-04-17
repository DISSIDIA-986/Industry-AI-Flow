import { fireEvent, render, screen } from '@testing-library/react'
import Navbar from '@/components/Navbar'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const pushMock = vi.fn()
const logoutMock = vi.fn()

const authState: {
  user: { name: string; email: string } | null
  logout: () => void
} = {
  user: { name: 'QA User', email: 'qa@example.com' },
  logout: logoutMock,
}

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  usePathname: () => '/',
}))

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => authState,
}))

describe('Navbar contracts', () => {
  beforeEach(() => {
    pushMock.mockReset()
    logoutMock.mockReset()
    authState.user = { name: 'QA User', email: 'qa@example.com' }
  })

  it('renders core navigation entries for shared shell routes', () => {
    render(<Navbar />)

    for (const navLabel of [
      'Dashboard',
      'Workflow chat',
      'Document management',
      'Data dashboard',
      'cost estimate',
      'APItest',
    ]) {
      expect(screen.getByRole('link', { name: navLabel })).toBeInTheDocument()
    }

    expect(screen.getByRole('link', { name: 'Industry AI Flow' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log out' })).toBeInTheDocument()
  })

  it('keeps logout workflow contract wired to auth and router', () => {
    render(<Navbar />)

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

    expect(logoutMock).toHaveBeenCalledTimes(1)
    expect(pushMock).toHaveBeenCalledWith('/login')
  })

  it('shows login/register controls when user session is absent', () => {
    authState.user = null

    render(<Navbar />)

    expect(screen.getByRole('link', { name: 'Log in' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'register' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Log out' })).not.toBeInTheDocument()
  })
})
