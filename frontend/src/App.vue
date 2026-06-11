<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { getStatus, sendAction, type MixerStatus } from '@/api/mixer'
import { getPresentationSlides, type PresentationSlide } from '@/api/presentation'
import PanelFrame from '@/components/PanelFrame.vue'
import ControlButton from '@/components/ui/ControlButton.vue'

type PageKey = 'recording' | 'slides' | 'finals' | 'audio' | 'tracking'

interface PageOption {
  key: PageKey
  label: string
}

interface QueueTrack {
  id: string
  label: string
}

const pages: PageOption[] = [
  { key: 'recording', label: 'Запись' },
  { key: 'slides', label: 'Слайды' },
  { key: 'finals', label: 'Финалы' },
  { key: 'audio', label: 'Звук' },
  { key: 'tracking', label: 'Камера' },
]

const recorderCameraURL = '/api/recorder/video?device=camera1'

const defaultStatus: MixerStatus = {
  recording: true,
  recordingTime: '1:23:56',
  fileSize: '2.4 GB',
  freeSpace: '184 GB',
  bitrate: '4500 kb/s',
  slide: 12,
  totalSlides: 32,
  nowPlaying: 'Im So',
  channels: [62, 47, 56, 68, 42, 52, 60, 58, 63, 49, 55, 44, 59, 61, 50, 57],
  meters: [62, 55, 36, 45, 61, 63, 51, 59, 58, 72, 36, 43, 61, 64, 50, 59],
  musicFiles: ['Im So.wav', 'Final.wav', 'My_favorite_unicorn.wav', 'Finalfin.wav'],
  tapeState: 1,
  tapeTime: 94,
  tapeLength: 205,
}

const currentPage = ref<PageKey>('recording')
const status = ref<MixerStatus>(defaultStatus)
const presentationSlides = ref<PresentationSlide[]>([])
const activeScenes = ref(new Set(['presentation']))
const selectedPreset = ref('green')
const trackingMode = ref<'head' | 'body'>('head')
let queueId = 0
const queue = ref(defaultStatus.musicFiles.slice(0, 4).map((file) => createQueueTrack(displayTrackName(file))))
const masterLevel = ref(69)
const draggedFader = ref<{ type: 'channel'; index: number } | { type: 'master' } | null>(null)
const draggedQueueIndex = ref<number | null>(null)
const draggedSoundboardLabel = ref<string | null>(null)
const queueDropIndex = ref<number | null>(null)

const isRecording = ref(false)
const isPaused = ref(false)
const elapsedSeconds = ref(0)
let timerInterval: ReturnType<typeof setInterval> | null = null
let statusInterval: ReturnType<typeof setInterval> | null = null

const formattedRecordingTime = computed(() => {
  const h = Math.floor(elapsedSeconds.value / 3600)
  const m = Math.floor((elapsedSeconds.value % 3600) / 60)
  const s = elapsedSeconds.value % 60
  return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

function startTimer() {
  timerInterval = setInterval(() => {
    elapsedSeconds.value++
  }, 1000)
}

function stopTimer() {
  if (timerInterval !== null) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function toggleRecording() {
  if (isRecording.value) {
    stopTimer()
    isRecording.value = false
    isPaused.value = false
    elapsedSeconds.value = 0
    void runAction('stop-recording')
  } else {
    isRecording.value = true
    isPaused.value = false
    elapsedSeconds.value = 0
    startTimer()
    void runAction('start-recording')
  }
}

function togglePause() {
  if (isPaused.value) {
    isPaused.value = false
    startTimer()
    void runAction('resume-recording')
  } else {
    isPaused.value = true
    stopTimer()
    void runAction('pause-recording')
  }
}

const soundboardItems = computed(() =>
  status.value.musicFiles.map((file, index) => ({
    id: `${index}-${file}`,
    label: displayTrackName(file),
    file,
  })),
)
const meters = computed(() => (status.value.meters.length > 0 ? status.value.meters : status.value.channels))
const tapeProgress = computed(() => {
  if (!status.value.tapeTime || !status.value.tapeLength) return 0
  return clamp((status.value.tapeTime / status.value.tapeLength) * 100, 0, 100)
})
const tapeTimeLabel = computed(() => `${formatDuration(status.value.tapeTime ?? 0)} / ${formatDuration(status.value.tapeLength ?? 0)}`)
const isTapePlaying = computed(() => status.value.tapeState === 1)
const tapeToggleLabel = computed(() => (isTapePlaying.value ? 'Пауза' : 'Продолжить'))
const tapeToggleSymbol = computed(() => (isTapePlaying.value ? 'Ⅱ' : '▶'))
const currentSlide = computed(() => presentationSlides.value[status.value.slide - 1])
const nextSlide = computed(() => presentationSlides.value[status.value.slide])

onMounted(async () => {
  try {
    await loadStatus()
    queue.value = status.value.musicFiles.slice(0, 4).map((file) => createQueueTrack(displayTrackName(file)))
  } catch {}
  statusInterval = setInterval(() => {
    void loadStatus()
  }, 1000)
})

onBeforeUnmount(() => {
  stopFaderDrag()
  stopTimer()
  if (statusInterval !== null) {
    clearInterval(statusInterval)
  }
})

async function loadStatus() {
  try {
    status.value = await getStatus()
  } catch {}
  try {
    presentationSlides.value = await getPresentationSlides()
  } catch {}
}

async function runAction(action: string, payload: Record<string, unknown> = {}) {
  try {
    await sendAction(action, payload)
    await loadStatus()
  } catch {}
}

function setPage(page: PageKey) {
  currentPage.value = page
  void runAction('open-page', { page })
}

function toggleScene(scene: string) {
  const next = new Set(activeScenes.value)
  if (next.has(scene)) {
    next.delete(scene)
  } else {
    next.add(scene)
  }
  activeScenes.value = next
  void runAction('toggle-scene', { scene })
}

function createQueueTrack(label: string): QueueTrack {
  queueId += 1
  return {
    id: `queue-${queueId}`,
    label,
  }
}

function displayTrackName(file: string): string {
  const parts = file.split('/')
  const name = parts[parts.length - 1] ?? file
  return name.replace(/\.(wav|mp3|flac)$/i, '')
}

function slideImageURL(slide: PresentationSlide): string {
  return slide.url
}

function formatDuration(value: number): string {
  const totalSeconds = Math.max(0, Math.round(value))
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function addTrackToQueue(label: string, index = queue.value.length) {
  const next = [...queue.value]
  const insertIndex = clamp(index, 0, next.length)
  next.splice(insertIndex, 0, createQueueTrack(label))
  queue.value = next
  void runAction('add-queue-track', { track: label, index: insertIndex })
}

function removeQueueTrack(index: number) {
  const next = [...queue.value]
  const [removed] = next.splice(index, 1)
  queue.value = next
  if (removed) {
    void runAction('remove-queue-track', { track: removed.label, index })
  }
}

function moveQueueTrack(fromIndex: number, toIndex: number) {
  const next = [...queue.value]
  const [track] = next.splice(fromIndex, 1)
  if (!track) return

  const adjustedIndex = fromIndex < toIndex ? toIndex - 1 : toIndex
  const insertIndex = clamp(adjustedIndex, 0, next.length)
  next.splice(insertIndex, 0, track)
  queue.value = next
  void runAction('move-queue-track', {
    track: track.label,
    from: fromIndex,
    to: insertIndex,
  })
}

function startSoundboardDrag(event: DragEvent, label: string) {
  draggedSoundboardLabel.value = label
  draggedQueueIndex.value = null
  event.dataTransfer?.setData('text/plain', label)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'copy'
  }
}

function startQueueDrag(event: DragEvent, index: number) {
  draggedQueueIndex.value = index
  draggedSoundboardLabel.value = null
  event.dataTransfer?.setData('text/plain', queue.value[index]?.label ?? '')
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function setQueueDropTarget(event: DragEvent, index = queue.value.length) {
  event.preventDefault()
  queueDropIndex.value = clamp(index, 0, queue.value.length)
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = draggedQueueIndex.value === null ? 'copy' : 'move'
  }
}

function handleQueueDrop(event: DragEvent, index = queue.value.length) {
  event.preventDefault()
  const targetIndex = clamp(index, 0, queue.value.length)

  if (draggedQueueIndex.value !== null) {
    moveQueueTrack(draggedQueueIndex.value, targetIndex)
  } else if (draggedSoundboardLabel.value !== null) {
    addTrackToQueue(draggedSoundboardLabel.value, targetIndex)
  }

  stopQueueDrag()
}

function stopQueueDrag() {
  draggedQueueIndex.value = null
  draggedSoundboardLabel.value = null
  queueDropIndex.value = null
}

function clearQueue() {
  queue.value = []
  void runAction('clear-queue')
}

function choosePreset(preset: string) {
  selectedPreset.value = preset
  void runAction('camera-preset', { preset })
}

function renderPage(page: PageKey): boolean {
  return currentPage.value === page
}

function levelFromPointer(event: PointerEvent, track: HTMLElement): number {
  const rect = track.getBoundingClientRect()
  const relativeY = clamp(event.clientY - rect.top, 0, rect.height)
  return Math.round(100 - (relativeY / rect.height) * 100)
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

function setChannelLevel(index: number, level: number) {
  const channels = [...status.value.channels]
  channels[index] = clamp(level, 0, 100)
  status.value = {
    ...status.value,
    channels,
  }
}

function updateDraggedFader(event: PointerEvent) {
  const current = draggedFader.value
  if (!current) return

  const track = (event.currentTarget ?? event.target) as HTMLElement
  const level = levelFromPointer(event, track)

  if (current.type === 'master') {
    masterLevel.value = clamp(level, 0, 100)
    return
  }

  setChannelLevel(current.index, level)
}

function startChannelFaderDrag(event: PointerEvent, index: number) {
  draggedFader.value = { type: 'channel', index }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  updateDraggedFader(event)
}

function startMasterFaderDrag(event: PointerEvent) {
  draggedFader.value = { type: 'master' }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  updateDraggedFader(event)
}

function stopFaderDrag() {
  const current = draggedFader.value
  if (!current) return

  draggedFader.value = null
  if (current.type === 'master') {
    void runAction('move-master', { value: masterLevel.value })
    return
  }

  void runAction('move-fader', {
    channel: current.index + 1,
    value: status.value.channels[current.index],
  })
}

function levelDeltaFromKey(event: KeyboardEvent): number | null {
  switch (event.key) {
    case 'ArrowUp':
    case 'ArrowRight':
      return 2
    case 'ArrowDown':
    case 'ArrowLeft':
      return -2
    case 'PageUp':
      return 10
    case 'PageDown':
      return -10
    default:
      return null
  }
}

function handleChannelFaderKey(event: KeyboardEvent, index: number) {
  if (event.key === 'Home') {
    event.preventDefault()
    setChannelLevel(index, 0)
    void runAction('move-fader', { channel: index + 1, value: 0 })
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    setChannelLevel(index, 100)
    void runAction('move-fader', { channel: index + 1, value: 100 })
    return
  }

  const delta = levelDeltaFromKey(event)
  if (delta === null) return

  event.preventDefault()
  const nextLevel = clamp(status.value.channels[index] + delta, 0, 100)
  setChannelLevel(index, nextLevel)
  void runAction('move-fader', { channel: index + 1, value: nextLevel })
}

function handleMasterFaderKey(event: KeyboardEvent) {
  if (event.key === 'Home') {
    event.preventDefault()
    masterLevel.value = 0
    void runAction('move-master', { value: masterLevel.value })
    return
  }
  if (event.key === 'End') {
    event.preventDefault()
    masterLevel.value = 100
    void runAction('move-master', { value: masterLevel.value })
    return
  }

  const delta = levelDeltaFromKey(event)
  if (delta === null) return

  event.preventDefault()
  masterLevel.value = clamp(masterLevel.value + delta, 0, 100)
  void runAction('move-master', { value: masterLevel.value })
}
</script>

<template>
  <main class="app-shell">
    <div class="single-page">
      <div class="page-content">
      <PanelFrame v-if="renderPage('recording')" title="Запись" :page="currentPage === 'recording'">
        <div class="recording-layout">
          <div class="timer-block">
            <div class="recording-dot" :class="{ 'is-recording': isRecording }">
              <span></span>
              {{ isPaused ? 'На паузе' : (isRecording ? 'Запись идет' : 'Готов') }}
            </div>
            <strong>{{ formattedRecordingTime }}</strong>
            <ControlButton :tone="isRecording ? 'danger' : 'success'" @click="toggleRecording">
              {{ isRecording ? 'Стоп' : 'Старт' }}
            </ControlButton>
            <ControlButton :tone="isPaused ? 'active' : 'default'" :disabled="!isRecording" @click="togglePause">
              {{ isPaused ? 'Продолжить' : 'Пауза' }}
            </ControlButton>
          </div>

          <div class="camera-grid">
            <div class="camera-card camera-card--wide">
              <span class="camera-led"></span>
              <span class="camera-title">Камера 1</span>
              <img class="camera-stream" :src="recorderCameraURL" alt="Поток камеры 1" />
            </div>
            <div class="camera-card">
              <span class="camera-led"></span>
              <span class="camera-title">Камера 2</span>
              <b>...</b>
            </div>
          </div>

          <div class="info-strip">
            <span>Размер файла</span>
            <span>Свободно</span>
            <span>Скорость записи</span>
          </div>

          <div class="meter-rack">
            <div v-for="(height, index) in meters" :key="index" class="meter">
              <span class="meter-label">{{ index === 0 ? '0' : '' }}</span>
              <i :style="{ height: `${height}%` }"></i>
            </div>
          </div>
        </div>
      </PanelFrame>

      <PanelFrame v-if="renderPage('slides')" title="Слайды" :page="currentPage === 'slides'">
        <div class="slides-layout">
          <div class="slide-previews">
            <button type="button" class="slide-preview" @click="runAction('select-slide', { slide: status.slide - 1 })">
              <img v-if="currentSlide" :src="slideImageURL(currentSlide)" :alt="`Текущий слайд ${status.slide}`" class="slide-preview-image" />
              <span v-else>...</span>
            </button>
            <button type="button" class="slide-preview" @click="runAction('select-slide', { slide: status.slide })">
              <img v-if="nextSlide" :src="slideImageURL(nextSlide)" :alt="`Следующий слайд ${status.slide + 1}`" class="slide-preview-image slide-preview-image--next" />
              <span v-else>...</span>
            </button>
          </div>
          <div class="slide-controls">
            <ControlButton tone="soft" @click="runAction('prev-slide')">← Назад</ControlButton>
            <strong>Слайд {{ status.slide }} / {{ status.totalSlides }}</strong>
            <ControlButton tone="soft" @click="runAction('next-slide')">Вперед →</ControlButton>
          </div>
          <div class="scene-panel">
            <div class="scene-buttons">
              <span>Сцены</span>
              <ControlButton tone="soft" @click="toggleScene('intro')">Заставка</ControlButton>
              <ControlButton tone="soft" @click="toggleScene('speaker')">Презентация + спикер</ControlButton>
              <ControlButton :tone="activeScenes.has('presentation') ? 'active' : 'soft'" @click="toggleScene('presentation')">
                Презентация
              </ControlButton>
              <ControlButton tone="soft" @click="toggleScene('intro-2')">Заставка 2</ControlButton>
              <ControlButton tone="soft" @click="toggleScene('camera')">Камера</ControlButton>
            </div>
            <ControlButton tone="soft" size="lg" @click="runAction('go-live')">Вывести</ControlButton>
          </div>
        </div>
      </PanelFrame>

      <PanelFrame v-if="renderPage('finals')" title="Финалы" :page="currentPage === 'finals'">
        <div class="finals-layout">
          <div class="final-grid" aria-label="Soundboard">
            <ControlButton
              v-for="item in soundboardItems"
              :key="item.id"
              tone="soft"
              size="lg"
              draggable="true"
              @click="runAction('play-final', { item: item.id, track: item.file })"
              @dragstart="startSoundboardDrag($event, item.label)"
              @dragend="stopQueueDrag"
            >
              {{ item.label }}
            </ControlButton>
          </div>
          <div class="player-panel">
            <div class="now-playing">
              <strong>Сейчас играет</strong>
              <span>{{ status.nowPlaying }}</span>
              <div class="progress-row">
                <i :style="{ width: `${tapeProgress}%` }"></i>
                <small>{{ tapeTimeLabel }}</small>
              </div>
              <div class="transport">
                <ControlButton aria-label="Назад" tone="soft" size="sm" @click="runAction('track-back')">↢</ControlButton>
                <ControlButton :aria-label="tapeToggleLabel" tone="soft" size="sm" @click="runAction('track-pause')">
                  {{ tapeToggleSymbol }}
                </ControlButton>
                <ControlButton aria-label="Вперед" tone="soft" size="sm" @click="runAction('track-forward')">↣</ControlButton>
              </div>
            </div>
            <ol
              class="queue-list"
              :class="{ 'is-drop-target': queueDropIndex === queue.length }"
              @dragover="setQueueDropTarget"
              @dragleave="queueDropIndex = null"
              @drop="handleQueueDrop"
            >
              <li
                v-for="(track, index) in queue"
                :key="track.id"
                draggable="true"
                :class="{ 'is-dragging': draggedQueueIndex === index, 'is-drop-target': queueDropIndex === index }"
                @dragstart="startQueueDrag($event, index)"
                @dragend="stopQueueDrag"
                @dragover="setQueueDropTarget($event, index)"
                @drop="handleQueueDrop($event, index)"
              >
                <button type="button" class="queue-track" @click="runAction('queue-track', { track: track.label, index })">
                  {{ index + 1 }}. {{ track.label }}
                </button>
                <button type="button" class="queue-delete" @click="removeQueueTrack(index)">Удалить</button>
              </li>
              <li v-if="queue.length === 0" class="queue-empty">Перетащите звук сюда</li>
            </ol>
            <ControlButton tone="soft" @click="clearQueue">Очистить очередь</ControlButton>
          </div>
        </div>
      </PanelFrame>

      <PanelFrame v-if="renderPage('audio')" title="Звук" :page="currentPage === 'audio'">
        <div class="audio-layout">
          <div class="channels">
            <div v-for="(value, index) in status.channels" :key="index" class="channel-strip">
              <ControlButton tone="pink" size="sm" @click="runAction('mute-channel', { channel: index + 1 })">mute</ControlButton>
              <ControlButton tone="active" size="sm" @click="runAction('select-channel', { channel: index + 1 })">Ch{{ index + 1 }}</ControlButton>
              <div
                class="fader"
                role="slider"
                tabindex="0"
                :aria-label="`Фейдер канала ${index + 1}`"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="value"
                @pointerdown="startChannelFaderDrag($event, index)"
                @pointermove="updateDraggedFader"
                @pointerup="stopFaderDrag"
                @pointercancel="stopFaderDrag"
                @keydown="handleChannelFaderKey($event, index)"
              >
                <span
                  aria-hidden="true"
                  :style="{ top: `${100 - value}%` }"
                ></span>
              </div>
            </div>
          </div>
          <div class="master-strip">
            <ControlButton tone="active" @click="runAction('select-master')">Master</ControlButton>
            <div
              class="master-fader"
              role="slider"
              tabindex="0"
              aria-label="Master fader"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="masterLevel"
              @pointerdown="startMasterFaderDrag"
              @pointermove="updateDraggedFader"
              @pointerup="stopFaderDrag"
              @pointercancel="stopFaderDrag"
              @keydown="handleMasterFaderKey"
            >
              <span aria-hidden="true" :style="{ top: `${100 - masterLevel}%` }"></span>
            </div>
            <ControlButton tone="pink" @click="runAction('mute-master')">mute</ControlButton>
          </div>
        </div>
      </PanelFrame>

      <PanelFrame v-if="renderPage('tracking')" title="Камера" :page="currentPage === 'tracking'">
        <div class="tracking-layout">
          <div class="tracking-preview">
            <span><i></i> Отслеживание активно</span>
            <b>...</b>
          </div>
          <div class="ptz-panel">
            <span>Управление</span>
            <div class="d-pad">
              <button type="button" class="up" aria-label="Вверх" @click="runAction('ptz-up')"></button>
              <button type="button" class="left" aria-label="Влево" @click="runAction('ptz-left')"></button>
              <button type="button" class="center" aria-label="Центр" @click="runAction('ptz-center')"></button>
              <button type="button" class="right" aria-label="Вправо" @click="runAction('ptz-right')"></button>
              <button type="button" class="down" aria-label="Вниз" @click="runAction('ptz-down')"></button>
            </div>
            <div class="zoom-controls">
              <ControlButton aria-label="Уменьшить" @click="runAction('zoom-out')">−</ControlButton>
              <ControlButton @click="runAction('zoom-reset')">Zoom</ControlButton>
              <ControlButton aria-label="Увеличить" @click="runAction('zoom-in')">＋</ControlButton>
            </div>
          </div>
          <div class="tracking-options">
            <ControlButton tone="success" size="lg" @click="runAction('disable-tracking')">Выключить умное следование</ControlButton>
            <label>
              <input v-model="trackingMode" type="radio" value="head" @change="runAction('tracking-mode', { mode: trackingMode })" />
              За головой
            </label>
            <label>
              <input v-model="trackingMode" type="radio" value="body" @change="runAction('tracking-mode', { mode: trackingMode })" />
              За телом
            </label>
          </div>
          <div class="preset-pad">
            <button
              v-for="preset in ['yellow', 'red', 'purple', 'green', 'cyan']"
              :key="preset"
              type="button"
              :class="['preset-button', `preset-button--${preset}`, selectedPreset === preset && 'is-selected']"
              :aria-label="`Пресет ${preset}`"
              @click="choosePreset(preset)"
            >
              ⊕
            </button>
          </div>
        </div>
      </PanelFrame>
      </div>

      <nav class="page-switcher" aria-label="Страницы микшера">
        <ControlButton
          v-for="page in pages"
          :key="page.key"
          size="sm"
          :tone="currentPage === page.key ? 'active' : 'soft'"
          :active="currentPage === page.key"
          @click="setPage(page.key)"
        >
          {{ page.label }}
        </ControlButton>
      </nav>
    </div>
  </main>
</template>
