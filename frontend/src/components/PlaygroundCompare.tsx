import type { PlaygroundResult } from '../types'
import { PlaygroundModelCard } from './PlaygroundModelCard'

interface PlaygroundCompareProps {
  results: PlaygroundResult[]
}

export function PlaygroundCompare({ results }: PlaygroundCompareProps) {
  if (results.length === 0) return null

  return (
    <div className={`grid gap-4 ${results.length === 2 ? 'grid-cols-1 md:grid-cols-2' : results.length === 3 ? 'grid-cols-1 md:grid-cols-3' : 'grid-cols-1'}`}>
      {results.map((result) => (
        <PlaygroundModelCard key={result.model} result={result} />
      ))}
    </div>
  )
}
