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

    // Labels must match src/components/Navbar.tsx verbatim. Earlier this
    // array had stale placeholders ("Workflow chat" lowercase, "Document
    // management", "Data dashboard", "cost estimate", "APItest") which
    // never matched the actual rendered links and red-ed CI on every push.
    for (const navLabel of [
      'Dashboard',
      'Workflow Chat',
      'Documents',
      'Dynamic Analytics',
      'Cost Estimation',
      'Intent Demo',
    ]) {
      expect(screen.getByRole('link', { name: navLabel })).toBeInTheDocument()
    }

    // Logo link. The rendered text is "Industry AI Flow" inside an <a>.
    expect(screen.getByRole('link', { name: /Industry AI Flow/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Log out' })).toBeInTheDocument()
  })

  it('delegates logout to auth context (AuthContext owns the redirect)', () => {
    // Navbar previously did router.push('/login') itself, racing with
    // AuthContext.logout's own redirect. The redirect is now centralized
    // in AuthContext, so Navbar must only call logout() and trust the
    // context to navigate.
    render(<Navbar />)

    fireEvent.click(screen.getByRole('button', { name: 'Log out' }))

    expect(logoutMock).toHaveBeenCalledTimes(1)
    expect(pushMock).not.toHaveBeenCalled()
  })

  it('shows login control when user session is absent', () => {
    // Register link was removed from the navbar (CLAUDE.md: "Register link
    // removed from navbar"), so the sign-out state is just a "Log in" link,
    // no "register" control. Log out button must still be absent.
    authState.user = null

    render(<Navbar />)

    expect(screen.getByRole('link', { name: 'Log in' })).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /register/i })
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Log out' })).not.toBeInTheDocument()
  })
})
