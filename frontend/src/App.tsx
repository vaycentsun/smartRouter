import { useState, useEffect } from 'react'

function App() {
  const [status, setStatus] = useState<string>('loading')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((data) => setStatus(data.status))
      .catch(() => setStatus('error'))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-3xl font-bold mb-4 text-gray-900">
        Smart Router Dashboard
      </h1>
      <div className="bg-white rounded-lg shadow p-6 max-w-md">
        <p className="text-gray-700">
          服务状态:{" "}
          <span className="font-mono font-semibold text-blue-600">
            {status}
          </span>
        </p>
        <p className="text-sm text-gray-500 mt-2">
          前端框架: React + Vite + TypeScript + Tailwind CSS
        </p>
      </div>
    </div>
  )
}

export default App
