import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/api/agent', () => ({
  deleteAgentSession: vi.fn(),
  getAgentMessageImage: vi.fn(),
  getAgentSession: vi.fn(),
  listAgentSessions: vi.fn().mockResolvedValue([]),
}))

import { listAgentSessions } from '@/api/agent'
import { useAgentStore } from '@/stores/agent'

describe('agent store user isolation', () => {
  beforeEach(() => {
    const values = new Map()
    vi.stubGlobal('localStorage', {
      getItem: (key) => values.get(key) ?? null,
      setItem: (key, value) => values.set(key, String(value)),
      removeItem: (key) => values.delete(key),
      clear: () => values.clear(),
    })
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('keeps each user current session and cached list in a separate namespace', () => {
    const store = useAgentStore()

    store.activateUser(1)
    store.currentSessionId = 'user-1-session'
    store.addMessage({ role: 'user', content: 'user one' })

    expect(localStorage.getItem('ssdd_agent_session:1')).toBe('user-1-session')
    expect(localStorage.getItem('ssdd_agent_sessions:1')).toContain('user-1-session')

    store.activateUser(2)
    expect(store.userScope).toBe('2')
    expect(store.currentSessionId).not.toBe('user-1-session')
    expect(store.messages).toEqual([])
    expect(store.sessions).toEqual([])

    store.currentSessionId = 'user-2-session'
    store.addMessage({ role: 'user', content: 'user two' })
    store.activateUser(1)

    expect(store.currentSessionId).toBe('user-1-session')
    expect(store.sessions[0].id).toBe('user-1-session')
    expect(localStorage.getItem('ssdd_agent_session:2')).toBe('user-2-session')
  })

  it('drops in-memory chat state on logout without deleting persisted user scope', () => {
    const store = useAgentStore()
    store.activateUser(7)
    store.currentSessionId = 'persistent-session'
    store.addMessage({ role: 'user', content: 'persist me' })

    store.clearUserScope()

    expect(store.userScope).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.sessions).toEqual([])
    expect(localStorage.getItem('ssdd_agent_session:7')).toBe('persistent-session')
  })

  it('keeps session owner metadata returned for an administrator', async () => {
    listAgentSessions.mockResolvedValueOnce([{
      id: 'other-user-session',
      owner_id: 9,
      owner_username: 'other-user',
      title: 'persisted chat',
    }])
    const store = useAgentStore()

    await store.fetchSessions(1)

    expect(store.sessions[0]).toMatchObject({
      id: 'other-user-session',
      ownerId: 9,
      ownerUsername: 'other-user',
    })
  })
})
