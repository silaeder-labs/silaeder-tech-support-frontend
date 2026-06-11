# Tech Support Mixer Prototype

Минимальный прототип интерфейса микшера для техподдержки.

## Запуск через Docker Compose

```bash
docker compose up --build
```

`docker-compose.yml` содержит ссылки на образы GHCR для сервисов, которые собираются из этого репозитория:

- `ghcr.io/silaeder-labs/silaeder-tech-support-frontend/mixer:latest`
- `ghcr.io/silaeder-labs/silaeder-tech-support-frontend/mock-mixer:latest`
- `ghcr.io/silaeder-labs/silaeder-tech-support-frontend/mock-camera:latest`
- `ghcr.io/silaeder-labs/silaeder-tech-support-frontend/mock-recorder:latest`
- `ghcr.io/silaeder-labs/obs-slides-site/presentation-clicker:latest`

При необходимости их можно переопределить через `MIXER_IMAGE`, `MOCK_MIXER_IMAGE`, `MOCK_CAMERA_IMAGE`, `MOCK_RECORDER_IMAGE` и `PRESENTATION_CLICKER_IMAGE`.

CI/CD собирает и публикует эти образы в GHCR. Для приватного `silaeder-labs/obs-slides-site` или публикации его образа из этого репозитория добавьте в GitHub Actions secret `OBS_SLIDES_SITE_TOKEN` или `GHCR_TOKEN` с доступом `contents:read` и `packages:write`.

После запуска сайт будет доступен на `http://localhost:8080`.
Мок X32 REST API для микшера будет доступен на `http://localhost:8090`.
Мок ESP32 Camera Turner API будет доступен на `http://localhost:8091`.
Мок xusb-recorder API будет доступен на `http://localhost:8093`; он отдает шумовой видеопоток на `/video`.
Presentation Clicker API будет доступен на `http://localhost:5056` и будет использовать данные из соседней директории `../obs-slides-site/data`.

Адреса внешних API лежат в `config/api.env`. Сейчас там docker-адреса mixer/camera mock-сервисов и реального presentation-clicker контейнера:

```env
MIXER_API_URL=http://mock-mixer:8090
CAMERA_API_URL=http://mock-camera:8091
RECORDER_API_URL=http://mock-recorder:8093
PRESENTATION_API_URL=http://presentation-clicker:5000
```

Для подключения реального оборудования поменяйте только значения в этом файле, например `http://192.168.1.50:8090`.

## Локальная разработка

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Backend:

```bash
cd backend
go mod download
MIXER_API_URL=http://localhost:8090 CAMERA_API_URL=http://localhost:8091 PRESENTATION_API_URL=http://localhost:8092 go run ./cmd/api
```

Backend проксирует mixer-данные и команды в `MIXER_API_URL`, команды камеры в `CAMERA_API_URL`, а команды презентаций в `PRESENTATION_API_URL`. Если mixer-переменная не задана или мок недоступен, `/api/status` вернет локальные демо-данные.

## Presentation API

Backend также отдает прокси-API для presentation clicker:

- `GET /api/presentation/state` - состояние текущей презентации.
- `GET /api/presentation/slides` - список подготовленных слайдов.
- `POST /api/presentation/prev` - перейти к предыдущему слайду.
- `POST /api/presentation/next` - перейти к следующему слайду.
- `POST /api/presentation/select` с JSON `{ "slide": 0 }` - выбрать слайд по zero-based индексу.
- `POST /api/presentation/rebuild` - пересобрать очередь презентаций.
- `POST /api/presentation/cache/clear` - очистить кэш презентаций.
- `POST /api/presentation/widget/cache` - обновить состояние OBS-виджета.
