export interface QuickTipDocument {
  name?: string
  status?: string
  chunk_count?: number
}

const READY_STATUSES = new Set(['processed', 'completed'])

function toFiniteNumber(value: unknown): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function normalizeName(name: string): string {
  return name.trim().replace(/\s+/g, ' ')
}

function hasKeyword(name: string, keywords: string[]): boolean {
  const lowered = name.toLowerCase()
  return keywords.some((keyword) => lowered.includes(keyword))
}

function appendUnique(target: string[], value?: string): void {
  if (!value) {
    return
  }
  const normalized = value.trim()
  if (!normalized) {
    return
  }
  if (!target.includes(normalized)) {
    target.push(normalized)
  }
}

function normalizeQuickTips(items: unknown[], maxCount: number): string[] {
  const normalized: string[] = []
  for (const item of items) {
    appendUnique(normalized, String(item || ''))
    if (normalized.length >= maxCount) {
      break
    }
  }
  return normalized
}

export function parsePinnedQuickTips(
  rawValue: string | undefined,
  maxCount = 5,
): string[] | null {
  const raw = String(rawValue || '').trim()
  if (!raw) {
    return null
  }

  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) {
      const normalized = normalizeQuickTips(parsed, maxCount)
      return normalized.length > 0 ? normalized : null
    }
  } catch {
    // Continue to non-JSON parsing fallback.
  }

  const items = raw.split('||').map((item) => item.trim())
  const normalized = normalizeQuickTips(items, maxCount)
  return normalized.length > 0 ? normalized : null
}

export function buildQuickTipsFromDocuments(
  documents: QuickTipDocument[],
  fallbackQuickTips: string[],
  maxCount = 8,
): string[] {
  const readyDocs = documents
    .map((item) => {
      const name = normalizeName(String(item?.name || ''))
      const status = String(item?.status || '').trim().toLowerCase()
      return {
        name,
        status,
        chunkCount: toFiniteNumber(item?.chunk_count),
      }
    })
    .filter((item) => item.name.length > 0 && READY_STATUSES.has(item.status))
    .sort((a, b) => b.chunkCount - a.chunkCount)

  if (readyDocs.length === 0) {
    return fallbackQuickTips.slice(0, maxCount)
  }

  const top = readyDocs[0]
  const second = readyDocs[1]
  const third = readyDocs[2]
  const safetyDoc =
    readyDocs.find((item) => hasKeyword(item.name, ['osha', 'cfr', 'safety'])) || undefined
  const concreteDoc =
    readyDocs.find((item) => hasKeyword(item.name, ['concrete', 'cast_in_place', 'ufgs_03_30_00'])) ||
    undefined
  const standardsDoc =
    readyDocs.find((item) => hasKeyword(item.name, ['gsa', 'p100', 'standard', 'specification', 'caltrans'])) ||
    undefined
  const ifcDoc =
    readyDocs.find((item) => hasKeyword(item.name, ['ifc', 'buildingsmart', 'schema'])) || undefined

  const generated: string[] = []

  appendUnique(
    generated,
    `Summarize the key requirements in "${top.name}" and cite the most relevant passages.`,
  )

  if (top && second) {
    appendUnique(
      generated,
      `Compare "${top.name}" and "${second.name}" on scope, mandatory requirements, and acceptance criteria.`,
    )
  }

  if (safetyDoc) {
    appendUnique(
      generated,
      `Based on "${safetyDoc.name}", create a practical site safety inspection checklist for a field engineer.`,
    )
  }

  if (concreteDoc) {
    const referenceDoc =
      standardsDoc && standardsDoc.name !== concreteDoc.name
        ? standardsDoc
        : second && second.name !== concreteDoc.name
        ? second
        : undefined

    appendUnique(
      generated,
      referenceDoc
        ? `For cast-in-place concrete work, which quality-control checkpoints in "${concreteDoc.name}" should align with "${referenceDoc.name}"?`
        : `From "${concreteDoc.name}", list the must-have quality-control and testing steps before pour approval.`,
    )
  }

  if (ifcDoc) {
    appendUnique(
      generated,
      `From "${ifcDoc.name}", which IFC entities and attributes are most important for BIM handover validation?`,
    )
  }

  if (standardsDoc && standardsDoc.name !== top.name) {
    appendUnique(
      generated,
      `What are the highest-priority compliance items in "${standardsDoc.name}" that teams often miss in design review?`,
    )
  }

  if (top && third) {
    appendUnique(
      generated,
      `Generate a pre-construction compliance checklist using "${top.name}" and "${third.name}".`,
    )
  }

  const merged = [...generated]
  for (const fallback of fallbackQuickTips) {
    appendUnique(merged, fallback)
    if (merged.length >= maxCount) {
      break
    }
  }

  return merged.slice(0, maxCount)
}
