export function getMediaUrl(path: string | null | undefined, baseUrl?: string): string | null {
    if (!path) return null;
    if (/^https?:\/\//i.test(path)) return path;

    try {
        const origin = new URL(baseUrl || window.location.origin, window.location.origin).origin;
        return new URL(path, origin).toString();
    } catch {
        return path;
    }
}
