import { existsSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

describe('AppHeader component', () => {
  it('exists in the layout components directory', () => {
    expect(existsSync(resolve(process.cwd(), 'src/components/layout/AppHeader.vue'))).toBe(true)
  })
})
