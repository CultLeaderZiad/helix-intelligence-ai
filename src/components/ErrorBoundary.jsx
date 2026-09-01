import React from "react"
import { AlertTriangle, RefreshCw } from "lucide-react"

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("Uncaught error caught by ErrorBoundary:", error, errorInfo)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-950 text-slate-100">
          <div className="max-w-md w-full p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl space-y-4 text-center">
            <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Something went wrong</h2>
              <p className="text-xs text-slate-400 mt-1">
                {this.state.error?.message || "An unexpected error occurred while rendering this page."}
              </p>
            </div>
            <button
              onClick={this.handleReset}
              className="px-4 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-semibold text-xs rounded-xl flex items-center justify-center gap-2 mx-auto transition"
            >
              <RefreshCw className="w-4 h-4" /> Reload Workspace
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
