const CHUNK_RELOAD_KEY = 'kapitbayan:chunk-reload-at'
const CHUNK_RELOAD_COOLDOWN_MS = 30_000

export function canRetryChunkLoad(
    storage: Pick<Storage, 'getItem' | 'setItem'>,
    now: number,
): boolean {
    try {
        const savedTimestamp = storage.getItem(CHUNK_RELOAD_KEY)
        if (savedTimestamp !== null) {
            const previousReloadAt = Number(savedTimestamp)
            if (Number.isFinite(previousReloadAt) && now - previousReloadAt < CHUNK_RELOAD_COOLDOWN_MS) {
                return false
            }
        }

        storage.setItem(CHUNK_RELOAD_KEY, String(now))
        return true
    } catch {
        // Avoid reloading when storage cannot retain the loop guard.
        return false
    }
}
