export const MAX_LOAD_LB = 80_000

export function parseLoad(value: string): number | null {
  const digits = value.replace(/[,\s]/g, '')
  if (!/^\d+$/.test(digits)) return null
  const load = Number(digits)
  return load >= 1 && load <= MAX_LOAD_LB ? load : null
}
