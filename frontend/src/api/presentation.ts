export interface PresentationSlide {
  index: number
  source: string
  local_number: number
  cache_key: string
  url: string
  file?: string
}

export async function getPresentationSlides(): Promise<PresentationSlide[]> {
  const response = await fetch('/api/presentation/slides')
  if (!response.ok) {
    throw new Error('Не удалось получить слайды презентации')
  }
  return response.json() as Promise<PresentationSlide[]>
}
