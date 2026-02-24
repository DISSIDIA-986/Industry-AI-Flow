import { describe, expect, it } from 'vitest'

import {
  buildQuickTipsFromDocuments,
  parsePinnedQuickTips,
} from '@/lib/workflow-quick-tips'

describe('buildQuickTipsFromDocuments', () => {
  const fallback = [
    'fallback-1',
    'fallback-2',
    'fallback-3',
    'fallback-4',
    'fallback-5',
  ]

  it('returns fallback tips when no processed documents are available', () => {
    const result = buildQuickTipsFromDocuments(
      [
        { name: 'construction_safety_regulations.pdf', status: 'processing', chunk_count: 0 },
        { name: 'material_cost_data.xlsx', status: 'failed', chunk_count: 0 },
      ],
      fallback,
    )

    expect(result).toEqual(fallback)
  })

  it('generates document-aware tips from processed vector docs', () => {
    const result = buildQuickTipsFromDocuments(
      [
        { name: 'gsa_p100_2024_final.pdf', status: 'processed', chunk_count: 2593 },
        { name: 'ufgs_03_30_00_cast_in_place_concrete.pdf', status: 'processed', chunk_count: 593 },
        { name: 'osha_29_cfr_1926.txt', status: 'processed', chunk_count: 71 },
        { name: 'buildingsmart_ifc_4_3_schema_specifications.txt', status: 'processed', chunk_count: 12 },
      ],
      fallback,
    )

    expect(result).toHaveLength(5)
    expect(result[0]).toContain('gsa_p100_2024_final.pdf')
    expect(result.some((item) => item.includes('osha_29_cfr_1926.txt'))).toBe(true)
    expect(
      result.some((item) =>
        item.includes('ufgs_03_30_00_cast_in_place_concrete.pdf'),
      ),
    ).toBe(true)
    expect(
      result.some((item) =>
        item.includes('buildingsmart_ifc_4_3_schema_specifications.txt'),
      ),
    ).toBe(true)
  })

  it('parses pinned quick tips from JSON array', () => {
    const result = parsePinnedQuickTips(
      JSON.stringify(['A', 'B', ' ', 'C', 'A']),
      5,
    )
    expect(result).toEqual(['A', 'B', 'C'])
  })

  it('parses pinned quick tips from || delimited string', () => {
    const result = parsePinnedQuickTips(
      'Tip 1 || Tip 2 ||  || Tip 3 || Tip 1',
      5,
    )
    expect(result).toEqual(['Tip 1', 'Tip 2', 'Tip 3'])
  })

  it('returns null when pinned quick tips input is empty', () => {
    expect(parsePinnedQuickTips('')).toBeNull()
    expect(parsePinnedQuickTips(undefined)).toBeNull()
  })
})
