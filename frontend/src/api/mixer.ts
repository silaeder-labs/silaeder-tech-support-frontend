export interface MixerStatus {
  recording: boolean
  recordingTime: string
  fileSize: string
  freeSpace: string
  bitrate: string
  slide: number
  totalSlides: number
  nowPlaying: string
  channels: number[]
  meters: number[]
  musicFiles: string[]
  tapeState?: number
  tapeTime?: number
  tapeLength?: number
}

export interface ActionResponse {
  ok: boolean
  action: string
  timestamp: string
}

export async function getStatus(): Promise<MixerStatus> {
  const response = await fetch('/api/status')
  if (!response.ok) {
    throw new Error('Не удалось получить состояние микшера')
  }
  return response.json() as Promise<MixerStatus>
}

export async function sendAction(action: string, payload: Record<string, unknown> = {}): Promise<ActionResponse> {
  const response = await fetch('/api/action', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ action, payload }),
  })

  if (!response.ok) {
    throw new Error('Команда не выполнена')
  }

  return response.json() as Promise<ActionResponse>
}
