import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

describe('ChatPage integration', () => {
  it('mounts the existing ChatInterface and agent store', () => {
    const page = readFileSync(resolve(process.cwd(), 'src/views/ChatPage.vue'), 'utf8')

    expect(page).toContain("import ChatInterface from '@/components/agent/ChatInterface.vue'")
    expect(page).toContain('<ChatInterface />')
    expect(page).toContain("import { useAgentStore } from '@/stores/agent'")
  })
})
