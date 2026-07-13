import { readFileSync } from 'fs'
import { resolve } from 'path'
import { describe, expect, it } from 'vitest'

describe('ChatPage integration', () => {
  it('renders the chat page with agent store and message list', () => {
    const page = readFileSync(resolve(process.cwd(), 'src/views/ChatPage.vue'), 'utf8')

    expect(page).toContain("import { useAgentStore } from '@/stores/agent'")
    expect(page).toContain("import MessageList from '@/components/agent/MessageList.vue'")
    expect(page).toContain('<MessageList')
  })
})
