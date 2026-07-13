import { existsSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

describe('AppHeader component', () => {
  it('exists in the layout components directory', () => {
    const componentPath = resolve(process.cwd(), 'src/components/layout/AppHeader.vue')

    expect(existsSync(componentPath)).toBe(true)
  })
})
