import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import { App } from './App'
import { canRetryChunkLoad } from './utils/chunkLoadRecovery'
import './index.css'

window.addEventListener('vite:preloadError', (event) => {
    event.preventDefault()

    // A phone can keep an older app shell open across a deployment. If its
    // dashboard chunk was removed, reload once so Vite can fetch the current
    // app shell and matching chunks. The session guard avoids reload loops
    // when a chunk remains unavailable.
    if (canRetryChunkLoad(window.sessionStorage, Date.now())) window.location.reload()
})

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <App />
        <Toaster
            position="bottom-right"
            toastOptions={{
                duration: 4000,
                success: {
                    style: {
                        background: '#f0fdf4',
                        border: '1px solid #bbf7d0',
                        color: '#166534',
                        fontWeight: '600',
                        fontSize: '14px',
                    },
                },
                error: {
                    style: {
                        background: '#fef2f2',
                        border: '1px solid #fecaca',
                        color: '#991b1b',
                        fontWeight: '600',
                        fontSize: '14px',
                    },
                },
            }}
        />
    </StrictMode>,
)
