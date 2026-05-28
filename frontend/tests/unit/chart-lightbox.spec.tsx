import { fireEvent, render, screen } from '@testing-library/react'
import { beforeAll, describe, expect, it, vi } from 'vitest'

import ChartLightbox, { type LightboxChart } from '@/components/ChartLightbox'

// jsdom versions vary in HTMLDialogElement support. Stub defensively so the
// component's showModal()/close() calls never throw inside tests.
beforeAll(() => {
  const proto = globalThis.HTMLDialogElement?.prototype
  if (!proto) return
  if (typeof proto.showModal !== 'function') {
    proto.showModal = function showModal(this: HTMLDialogElement) {
      this.setAttribute('open', '')
    }
  }
  if (typeof proto.close !== 'function') {
    proto.close = function close(this: HTMLDialogElement) {
      this.removeAttribute('open')
    }
  }
})

const charts: LightboxChart[] = [
  { url: '/c1.png', type: 'histogram', summary: 'mean=12' },
  { url: '/c2.png', type: 'scatter', summary: 'r=0.8' },
  { url: '/c3.png', type: 'bar', summary: null },
]

describe('ChartLightbox', () => {
  it('renders counter starting at startIndex', () => {
    render(<ChartLightbox charts={charts} open startIndex={1} onClose={() => {}} />)
    expect(screen.getByTestId('chart-lightbox-counter').textContent).toBe('Chart 2 of 3')
  })

  it('arrow right advances, arrow left retreats, bounds are enforced', () => {
    render(<ChartLightbox charts={charts} open startIndex={0} onClose={() => {}} />)
    const dialog = screen.getByTestId('chart-lightbox')
    const counter = screen.getByTestId('chart-lightbox-counter')

    // 0 → cannot go prev (stays at 0)
    fireEvent.keyDown(dialog, { key: 'ArrowLeft' })
    expect(counter.textContent).toBe('Chart 1 of 3')

    // 0 → 1 → 2 via right arrow
    fireEvent.keyDown(dialog, { key: 'ArrowRight' })
    expect(counter.textContent).toBe('Chart 2 of 3')
    fireEvent.keyDown(dialog, { key: 'ArrowRight' })
    expect(counter.textContent).toBe('Chart 3 of 3')

    // bounds: cannot go past last
    fireEvent.keyDown(dialog, { key: 'ArrowRight' })
    expect(counter.textContent).toBe('Chart 3 of 3')

    // back to first
    fireEvent.keyDown(dialog, { key: 'ArrowLeft' })
    fireEvent.keyDown(dialog, { key: 'ArrowLeft' })
    expect(counter.textContent).toBe('Chart 1 of 3')
  })

  it('prev/next buttons disable at bounds', () => {
    render(<ChartLightbox charts={charts} open startIndex={0} onClose={() => {}} />)
    expect(screen.getByTestId('chart-lightbox-prev')).toBeDisabled()
    expect(screen.getByTestId('chart-lightbox-next')).not.toBeDisabled()

    fireEvent.click(screen.getByTestId('chart-lightbox-next'))
    fireEvent.click(screen.getByTestId('chart-lightbox-next'))
    expect(screen.getByTestId('chart-lightbox-next')).toBeDisabled()
    expect(screen.getByTestId('chart-lightbox-prev')).not.toBeDisabled()
  })

  it('close button fires onClose', () => {
    const onClose = vi.fn()
    render(<ChartLightbox charts={charts} open startIndex={0} onClose={onClose} />)
    fireEvent.click(screen.getByTestId('chart-lightbox-close'))
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('cancel event on dialog (simulates ESC) fires onClose', () => {
    const onClose = vi.fn()
    render(<ChartLightbox charts={charts} open startIndex={0} onClose={onClose} />)
    const dialog = screen.getByTestId('chart-lightbox')
    // React wires onCancel to the native cancel event; ESC on native dialog fires cancel
    fireEvent(dialog, new Event('cancel', { bubbles: false, cancelable: true }))
    expect(onClose).toHaveBeenCalled()
  })

  it('does not render prev/next when only one chart', () => {
    render(
      <ChartLightbox
        charts={[{ url: '/a.png', type: 'chart' }]}
        open
        startIndex={0}
        onClose={() => {}}
      />,
    )
    expect(screen.queryByTestId('chart-lightbox-prev')).toBeNull()
    expect(screen.queryByTestId('chart-lightbox-next')).toBeNull()
  })

  it('renders nothing when charts array is empty', () => {
    const { container } = render(
      <ChartLightbox charts={[]} open startIndex={0} onClose={() => {}} />,
    )
    expect(container.querySelector('[data-testid="chart-lightbox"]')).toBeNull()
  })
})
