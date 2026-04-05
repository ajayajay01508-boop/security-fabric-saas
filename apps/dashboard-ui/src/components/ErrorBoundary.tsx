import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: React.ReactNode
  fallback?: React.ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, info)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: undefined })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex flex-col items-center justify-center min-h-64 p-8 text-center">
          <AlertTriangle className="w-10 h-10 text-fabric-high mb-4" />
          <h2 className="font-display text-lg font-bold text-white mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-fabric-dim font-body mb-1 max-w-sm">
            An unexpected error occurred in this section of the dashboard.
          </p>
          {this.state.error && (
            <p className="text-xs font-mono text-fabric-dim/60 mb-5 max-w-sm truncate">
              {this.state.error.message}
            </p>
          )}
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 text-xs font-mono text-fabric-accent border border-fabric-accent/40
                       bg-fabric-accent/10 hover:bg-fabric-accent/20 px-4 py-2 rounded-lg transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
