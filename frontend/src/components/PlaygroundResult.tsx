import type { PlaygroundResult as PlaygroundResultType } from '../types'
import { PlaygroundModelCard } from './PlaygroundModelCard'

interface PlaygroundResultProps {
  result: PlaygroundResultType
}

export function PlaygroundResult({ result }: PlaygroundResultProps) {
  return (
    <div className="space-y-4">
      <PlaygroundModelCard result={result} />
    </div>
  )
}
