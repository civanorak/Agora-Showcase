import { Component } from 'react'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

/**
 * Catches render-time crashes so an unexpected throw shows a readable message
 * instead of an infinite blank white screen. This is a safety net — not a
 * replacement for handling errors where they happen.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: unknown) {
    console.error('AGORA crashed while rendering:', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: 24,
            textAlign: 'center',
            fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            background: '#f6f5f2',
            color: '#2c2c31',
          }}
        >
          <strong style={{ fontSize: 16 }}>Something went wrong.</strong>
          <span style={{ fontSize: 13, color: '#6f6e6a' }}>
            Please reload the page. If it keeps happening, try again in a moment.
          </span>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: 8,
              padding: '8px 16px',
              fontSize: 13,
              fontWeight: 600,
              color: '#ffffff',
              background: '#35857b',
              border: 'none',
              borderRadius: 7,
              cursor: 'pointer',
            }}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
