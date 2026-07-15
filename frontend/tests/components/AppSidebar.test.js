import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

const sidebar = readFileSync(
  resolve(process.cwd(), 'src/components/layout/AppSidebar.vue'),
  'utf8',
)

describe('AppSidebar user menu', () => {
  it('keeps the settings entry explicit while the settings page is unavailable', () => {
    expect(sidebar).toContain('command="settings"')
    expect(sidebar).toContain("if (command === 'settings')")
    expect(sidebar).toContain("ElMessage.info('设置功能暂未开放')")
  })
})
