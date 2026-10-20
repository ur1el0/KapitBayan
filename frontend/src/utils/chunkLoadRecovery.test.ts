import { describe, expect, it } from 'vitest'
import { canRetryChunkLoad } from './chunkLoadRecovery'

const key = 'kapitbayan:chunk-reload-at'

describe('canRetryChunkLoad', () => {
    it('allows one reload and records its time', () => {
        const storage = new Map<string, string>()
        const sessionStorage = {
            getItem: (item: string) => storage.get(item) ?? null,
            setItem: (item: string, value: string) => storage.set(item, value),
        }

        expect(canRetryChunkLoad(sessionStorage, 0)).toBe(true)
        expect(storage.get(key)).toBe('0')
    })

    it('blocks another reload within the cooldown and permits one after it', () => {
        const storage = new Map([[key, '100000']])
        const sessionStorage = {
            getItem: (item: string) => storage.get(item) ?? null,
            setItem: (item: string, value: string) => storage.set(item, value),
        }

        expect(canRetryChunkLoad(sessionStorage, 129_999)).toBe(false)
        expect(canRetryChunkLoad(sessionStorage, 130_000)).toBe(true)
        expect(storage.get(key)).toBe('130000')
    })

    it('keeps the error boundary when session storage is unavailable', () => {
        const sessionStorage = {
            getItem: () => { throw new Error('Storage unavailable') },
            setItem: () => { throw new Error('Storage unavailable') },
        }

        expect(canRetryChunkLoad(sessionStorage, 100_000)).toBe(false)
    })
})
