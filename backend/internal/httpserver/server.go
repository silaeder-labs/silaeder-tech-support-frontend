package httpserver

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

type Server struct {
	echo               *echo.Echo
	staticDir          string
	mixerAPIURL        string
	cameraAPIURL       string
	presentationAPIURL string
	recorderAPIURL     string
	httpClient         *http.Client
	streamClient       *http.Client
}

type statusResponse struct {
	Recording     bool     `json:"recording"`
	RecordingTime string   `json:"recordingTime"`
	FileSize      string   `json:"fileSize"`
	FreeSpace     string   `json:"freeSpace"`
	Bitrate       string   `json:"bitrate"`
	Slide         int      `json:"slide"`
	TotalSlides   int      `json:"totalSlides"`
	NowPlaying    string   `json:"nowPlaying"`
	Channels      []int    `json:"channels"`
	Meters        []int    `json:"meters"`
	MusicFiles    []string `json:"musicFiles"`
	TapeState     *int     `json:"tapeState,omitempty"`
	TapeTime      *float64 `json:"tapeTime,omitempty"`
	TapeLength    *float64 `json:"tapeLength,omitempty"`
}

type actionRequest struct {
	Action  string         `json:"action"`
	Payload map[string]any `json:"payload"`
}

type actionResponse struct {
	OK        bool   `json:"ok"`
	Action    string `json:"action"`
	Timestamp string `json:"timestamp"`
}

type usbStatusResponse struct {
	Mounted    bool     `json:"mounted"`
	Path       *string  `json:"path"`
	TapeFile   *string  `json:"tape_file"`
	TapeState  *int     `json:"tape_state"`
	TapeTime   *float64 `json:"tape_time"`
	TapeLength *float64 `json:"tape_length"`
}

type usbListResponse struct {
	Path  string   `json:"path"`
	Files []string `json:"files"`
}

type presentationStateResponse struct {
	CurrentIndex int                         `json:"current_index"`
	Total        int                         `json:"total"`
	Status       string                      `json:"status"`
	Busy         bool                        `json:"busy"`
	Version      int                         `json:"version"`
	Slide        *presentationSlideResponse  `json:"slide"`
	ObsWidget    *presentationWidgetState    `json:"obs_widget"`
	Slides       []presentationSlideResponse `json:"slides,omitempty"`
	TotalSlides  int                         `json:"totalSlides,omitempty"`
}

type presentationSlideResponse struct {
	Index       int    `json:"index"`
	Source      string `json:"source"`
	LocalNumber int    `json:"local_number"`
	CacheKey    string `json:"cache_key"`
	URL         string `json:"url"`
	File        string `json:"file,omitempty"`
}

type presentationWidgetState struct {
	Connected     bool   `json:"connected"`
	CurrentIndex  int    `json:"current_index"`
	ReadyCount    int    `json:"ready_count"`
	DesiredCount  int    `json:"desired_count"`
	RetainedCount int    `json:"retained_count"`
	UpdatedAt     string `json:"updated_at,omitempty"`
}

func New(staticDir string) *Server {
	e := echo.New()
	e.HideBanner = true
	e.Use(middleware.Recover())
	e.Use(middleware.CORS())

	s := &Server{
		echo:               e,
		staticDir:          staticDir,
		mixerAPIURL:        strings.TrimRight(os.Getenv("MIXER_API_URL"), "/"),
		cameraAPIURL:       strings.TrimRight(os.Getenv("CAMERA_API_URL"), "/"),
		presentationAPIURL: strings.TrimRight(os.Getenv("PRESENTATION_API_URL"), "/"),
		recorderAPIURL:     strings.TrimRight(os.Getenv("RECORDER_API_URL"), "/"),
		httpClient:         &http.Client{Timeout: 3 * time.Second},
		streamClient:       &http.Client{},
	}
	e.GET("/api/status", s.status)
	e.POST("/api/action", s.action)
	e.GET("/api/presentation/state", s.presentationState)
	e.GET("/api/presentation/slides", s.presentationSlides)
	e.POST("/api/presentation/next", s.presentationNext)
	e.POST("/api/presentation/prev", s.presentationPrev)
	e.POST("/api/presentation/select", s.presentationSelect)
	e.POST("/api/presentation/rebuild", s.presentationRebuild)
	e.POST("/api/presentation/cache/clear", s.presentationClearCache)
	e.POST("/api/presentation/widget/cache", s.presentationWidgetCache)
	e.GET("/api/recorder/video", s.recorderVideoStream)
	e.GET("/api/health", s.health)
	e.GET("/slides/*", s.presentationSlideAsset)
	e.GET("/", s.frontend)
	e.GET("/*", s.frontend)

	return s
}

func (s *Server) Start(address string) error {
	return s.echo.Start(address)
}

func (s *Server) health(c echo.Context) error {
	return c.JSON(http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) frontend(c echo.Context) error {
	requested := strings.TrimPrefix(c.Param("*"), "/")
	if requested == "" {
		return c.File(filepath.Join(s.staticDir, "index.html"))
	}

	cleanPath := filepath.Clean(requested)
	if strings.HasPrefix(cleanPath, "..") {
		return c.File(filepath.Join(s.staticDir, "index.html"))
	}

	fullPath := filepath.Join(s.staticDir, cleanPath)
	if info, err := os.Stat(fullPath); err == nil && !info.IsDir() {
		return c.File(fullPath)
	}

	return c.File(filepath.Join(s.staticDir, "index.html"))
}

func (s *Server) status(c echo.Context) error {
	if s.mixerAPIURL != "" {
		var status statusResponse
		if err := s.mixerRequest(c.Request().Context(), http.MethodGet, "/api/status", nil, &status); err == nil {
			s.enrichStatusFromMixer(c.Request().Context(), &status)
			s.enrichStatusFromPresentation(c.Request().Context(), &status)
			return c.JSON(http.StatusOK, status)
		}
	}

	status := statusResponse{
		Recording:     true,
		RecordingTime: "1:23:56",
		FileSize:      "2.4 GB",
		FreeSpace:     "184 GB",
		Bitrate:       "4500 kb/s",
		Slide:         12,
		TotalSlides:   32,
		NowPlaying:    "Im So",
		Channels:      []int{62, 47, 56, 68, 42, 52, 60, 58, 63, 49, 55, 44, 59, 61, 50, 57},
		Meters:        []int{62, 55, 36, 45, 61, 63, 51, 59, 58, 72, 36, 43, 61, 64, 50, 59},
		MusicFiles:    []string{"Im So.wav", "Final.wav", "My_favorite_unicorn.wav", "Finalfin.wav"},
	}
	s.enrichStatusFromPresentation(c.Request().Context(), &status)
	return c.JSON(http.StatusOK, status)
}

func (s *Server) enrichStatusFromMixer(ctx context.Context, status *statusResponse) {
	var usb usbStatusResponse
	if err := s.mixerRequest(ctx, http.MethodGet, "/api/usb", nil, &usb); err == nil {
		if usb.TapeFile != nil && *usb.TapeFile != "" {
			status.NowPlaying = displayTrackName(*usb.TapeFile)
		}
		status.TapeState = usb.TapeState
		status.TapeTime = usb.TapeTime
		status.TapeLength = usb.TapeLength
	}

	var list usbListResponse
	if err := s.mixerRequest(ctx, http.MethodGet, "/api/usb/list", nil, &list); err == nil {
		status.MusicFiles = list.Files
	}

	if len(status.Meters) == 0 {
		status.Meters = status.Channels
	}
	if len(status.MusicFiles) == 0 {
		status.MusicFiles = []string{"Im So.wav", "Final.wav", "My_favorite_unicorn.wav", "Finalfin.wav"}
	}
}

func (s *Server) enrichStatusFromPresentation(ctx context.Context, status *statusResponse) {
	var presentation presentationStateResponse
	if err := s.presentationRequest(ctx, http.MethodGet, "/api/state", nil, &presentation); err != nil {
		return
	}
	if presentation.Total > 0 {
		status.Slide = presentation.CurrentIndex + 1
		status.TotalSlides = presentation.Total
	}
}

func (s *Server) presentationState(c echo.Context) error {
	var state presentationStateResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodGet, "/api/state", nil, &state); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationSlides(c echo.Context) error {
	var slides []presentationSlideResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodGet, "/api/slides", nil, &slides); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, slides)
}

func (s *Server) presentationNext(c echo.Context) error {
	var state presentationStateResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodPost, "/api/next", nil, &state); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationPrev(c echo.Context) error {
	var state presentationStateResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodPost, "/api/prev", nil, &state); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationSelect(c echo.Context) error {
	var req struct {
		Slide int `json:"slide"`
	}
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Некорректный номер слайда"})
	}

	state, err := s.selectPresentationIndex(c.Request().Context(), req.Slide)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationRebuild(c echo.Context) error {
	var state presentationStateResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodPost, "/api/rebuild", nil, &state); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationClearCache(c echo.Context) error {
	var state presentationStateResponse
	if err := s.presentationRequest(c.Request().Context(), http.MethodPost, "/api/cache/clear", nil, &state); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, state)
}

func (s *Server) presentationWidgetCache(c echo.Context) error {
	var payload map[string]any
	if err := c.Bind(&payload); err != nil && !errors.Is(err, io.EOF) {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Некорректное состояние виджета"})
	}

	var response map[string]any
	if err := s.presentationRequest(c.Request().Context(), http.MethodPost, "/api/widget/cache", payload, &response); err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	return c.JSON(http.StatusOK, response)
}

func (s *Server) presentationSlideAsset(c echo.Context) error {
	if s.presentationAPIURL == "" {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}

	u, err := url.JoinPath(s.presentationAPIURL, "slides", c.Param("*"))
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Некорректный адрес слайда"})
	}

	request, err := http.NewRequestWithContext(c.Request().Context(), http.MethodGet, u, nil)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Некорректный запрос слайда"})
	}

	response, err := s.httpClient.Do(request)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Presentation API недоступен"})
	}
	defer response.Body.Close()

	contentType := response.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/octet-stream"
	}
	return c.Stream(response.StatusCode, contentType, response.Body)
}

func (s *Server) recorderVideoStream(c echo.Context) error {
	if s.recorderAPIURL == "" {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Recorder API недоступен"})
	}

	u, err := url.JoinPath(s.recorderAPIURL, "video")
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Некорректный адрес видеопотока"})
	}
	if rawQuery := c.QueryString(); rawQuery != "" {
		u += "?" + rawQuery
	}

	request, err := http.NewRequestWithContext(c.Request().Context(), http.MethodGet, u, nil)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Некорректный запрос видеопотока"})
	}

	response, err := s.streamClient.Do(request)
	if err != nil {
		return c.JSON(http.StatusBadGateway, map[string]string{"error": "Recorder API недоступен"})
	}
	defer response.Body.Close()

	contentType := response.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "multipart/x-mixed-replace; boundary=frame"
	}
	return c.Stream(response.StatusCode, contentType, response.Body)
}

func (s *Server) action(c echo.Context) error {
	var req actionRequest
	if err := c.Bind(&req); err != nil {
		return c.JSON(http.StatusBadRequest, map[string]string{"error": "Некорректная команда"})
	}
	if req.Action == "" {
		req.Action = "noop"
	}

	if s.mixerAPIURL != "" || s.cameraAPIURL != "" || s.presentationAPIURL != "" {
		if err := s.forwardAction(c.Request().Context(), req); err != nil {
			return c.JSON(http.StatusBadGateway, map[string]string{"error": "Внешний сервис недоступен"})
		}
	}

	return c.JSON(http.StatusOK, actionResponse{
		OK:        true,
		Action:    req.Action,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) forwardAction(ctx context.Context, req actionRequest) error {
	switch req.Action {
	case "ptz-left":
		return s.rotateCamera(ctx, -10)
	case "ptz-right":
		return s.rotateCamera(ctx, 10)
	case "ptz-up":
		return s.rotateCamera(ctx, 5)
	case "ptz-down":
		return s.rotateCamera(ctx, -5)
	case "ptz-center", "zoom-reset":
		return s.moveCamera(ctx, 0)
	case "disable-tracking":
		return s.cameraRequest(ctx, "/disable", nil)
	case "tracking-mode":
		return s.cameraRequest(ctx, "/enable", nil)
	case "camera-preset":
		return s.cameraPreset(ctx, req)
	case "zoom-in", "zoom-out":
		return s.cameraRequest(ctx, "/status", nil)
	case "prev-slide":
		return s.presentationRequest(ctx, http.MethodPost, "/api/prev", nil, nil)
	case "next-slide":
		return s.presentationRequest(ctx, http.MethodPost, "/api/next", nil, nil)
	case "select-slide":
		return s.selectPresentationSlide(ctx, req)
	case "move-fader":
		channel, ok := numberPayload(req.Payload, "channel")
		if !ok {
			return s.sendXRemote(ctx, req)
		}
		value, _ := numberPayload(req.Payload, "value")
		return s.mixerRequest(ctx, http.MethodPatch, fmt.Sprintf("/api/channels/%d", int(channel)), map[string]float64{
			"fader": value / 100,
		}, nil)
	case "move-master":
		value, _ := numberPayload(req.Payload, "value")
		return s.mixerRequest(ctx, http.MethodPatch, "/api/main/st", map[string]float64{
			"fader": value / 100,
		}, nil)
	case "clear-queue":
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/stop", nil, nil)
	case "stop-recording":
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/stop", nil, nil)
	case "pause-recording":
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/pause", nil, nil)
	case "track-back":
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/prev", nil, nil)
	case "track-forward":
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/next", nil, nil)
	case "track-pause":
		return s.toggleTape(ctx)
	case "play-final", "queue-track":
		track, ok := stringPayload(req.Payload, "track")
		if !ok {
			return s.sendXRemote(ctx, req)
		}
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/play", map[string]string{"name": track}, nil)
	case "open-page", "toggle-scene", "noop":
		return s.sendXRemote(ctx, req)
	default:
		return s.sendXRemote(ctx, req)
	}
}

func (s *Server) toggleTape(ctx context.Context) error {
	var usb usbStatusResponse
	if err := s.mixerRequest(ctx, http.MethodGet, "/api/usb", nil, &usb); err != nil {
		return err
	}
	if usb.TapeState != nil && *usb.TapeState == 1 {
		return s.mixerRequest(ctx, http.MethodPost, "/api/usb/pause", nil, nil)
	}
	return s.mixerRequest(ctx, http.MethodPost, "/api/usb/play", nil, nil)
}

func (s *Server) rotateCamera(ctx context.Context, degrees float64) error {
	if s.cameraAPIURL == "" {
		return s.sendXRemote(ctx, actionRequest{Action: "camera-unavailable"})
	}
	return s.cameraRequest(ctx, "/rotate", url.Values{
		"deg":   []string{fmt.Sprintf("%.2f", degrees)},
		"speed": []string{"45"},
	})
}

func (s *Server) moveCamera(ctx context.Context, degrees float64) error {
	if s.cameraAPIURL == "" {
		return s.sendXRemote(ctx, actionRequest{Action: "camera-unavailable"})
	}
	return s.cameraRequest(ctx, "/move", url.Values{
		"deg":   []string{fmt.Sprintf("%.2f", degrees)},
		"speed": []string{"60"},
	})
}

func (s *Server) cameraPreset(ctx context.Context, req actionRequest) error {
	preset, _ := req.Payload["preset"].(string)
	degreesByPreset := map[string]float64{
		"yellow": -60,
		"red":    -30,
		"purple": 0,
		"green":  30,
		"cyan":   60,
	}
	degrees, ok := degreesByPreset[preset]
	if !ok {
		return s.cameraRequest(ctx, "/status", nil)
	}

	return s.moveCamera(ctx, degrees)
}

func (s *Server) sendXRemote(ctx context.Context, req actionRequest) error {
	return s.mixerRequest(ctx, http.MethodPost, "/api/xremote", map[string]any{
		"last_action": req.Action,
		"payload":     req.Payload,
	}, nil)
}

func numberPayload(payload map[string]any, key string) (float64, bool) {
	value, ok := payload[key]
	if !ok {
		return 0, false
	}

	switch typed := value.(type) {
	case float64:
		return typed, true
	case int:
		return float64(typed), true
	case json.Number:
		parsed, err := typed.Float64()
		return parsed, err == nil
	default:
		return 0, false
	}
}

func stringPayload(payload map[string]any, key string) (string, bool) {
	value, ok := payload[key]
	if !ok {
		return "", false
	}
	typed, ok := value.(string)
	return typed, ok && typed != ""
}

func displayTrackName(name string) string {
	name = strings.TrimSuffix(name, ".wav")
	name = strings.TrimSuffix(name, ".mp3")
	name = strings.TrimSuffix(name, ".flac")
	parts := strings.Split(name, "/")
	return parts[len(parts)-1]
}

func (s *Server) mixerRequest(ctx context.Context, method string, path string, payload any, target any) error {
	if s.mixerAPIURL == "" {
		return nil
	}

	u, err := url.JoinPath(s.mixerAPIURL, path)
	if err != nil {
		return fmt.Errorf("build mixer url: %w", err)
	}

	var body io.Reader
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("marshal mixer request: %w", err)
		}
		body = bytes.NewReader(raw)
	}

	request, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return fmt.Errorf("create mixer request: %w", err)
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}

	response, err := s.httpClient.Do(request)
	if err != nil {
		return fmt.Errorf("call mixer: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("mixer returned status %d", response.StatusCode)
	}

	if target == nil {
		_, _ = io.Copy(io.Discard, response.Body)
		return nil
	}
	if err := json.NewDecoder(response.Body).Decode(target); err != nil {
		return fmt.Errorf("decode mixer response: %w", err)
	}

	return nil
}

func (s *Server) cameraRequest(ctx context.Context, path string, query url.Values) error {
	if s.cameraAPIURL == "" {
		return nil
	}

	u, err := url.JoinPath(s.cameraAPIURL, path)
	if err != nil {
		return fmt.Errorf("build camera url: %w", err)
	}
	if len(query) > 0 {
		u += "?" + query.Encode()
	}

	request, err := http.NewRequestWithContext(ctx, http.MethodGet, u, nil)
	if err != nil {
		return fmt.Errorf("create camera request: %w", err)
	}

	response, err := s.httpClient.Do(request)
	if err != nil {
		return fmt.Errorf("call camera: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("camera returned status %d", response.StatusCode)
	}

	_, _ = io.Copy(io.Discard, response.Body)
	return nil
}

func (s *Server) selectPresentationSlide(ctx context.Context, req actionRequest) error {
	slide, ok := numberPayload(req.Payload, "slide")
	if !ok {
		return nil
	}
	_, err := s.selectPresentationIndex(ctx, int(slide))
	return err
}

func (s *Server) selectPresentationIndex(ctx context.Context, targetIndex int) (presentationStateResponse, error) {
	var state presentationStateResponse
	if err := s.presentationRequest(ctx, http.MethodGet, "/api/state", nil, &state); err != nil {
		return presentationStateResponse{}, err
	}
	if state.Total == 0 || state.Busy {
		return state, nil
	}

	if targetIndex < 0 {
		targetIndex = 0
	}
	if targetIndex >= state.Total {
		targetIndex = state.Total - 1
	}

	for state.CurrentIndex < targetIndex {
		if err := s.presentationRequest(ctx, http.MethodPost, "/api/next", nil, &state); err != nil {
			return presentationStateResponse{}, err
		}
	}
	for state.CurrentIndex > targetIndex {
		if err := s.presentationRequest(ctx, http.MethodPost, "/api/prev", nil, &state); err != nil {
			return presentationStateResponse{}, err
		}
	}

	return state, nil
}

func (s *Server) presentationRequest(ctx context.Context, method string, path string, payload any, target any) error {
	if s.presentationAPIURL == "" {
		return errors.New("presentation api url is not configured")
	}

	u, err := url.JoinPath(s.presentationAPIURL, path)
	if err != nil {
		return fmt.Errorf("build presentation url: %w", err)
	}

	var body io.Reader
	if payload != nil {
		raw, err := json.Marshal(payload)
		if err != nil {
			return fmt.Errorf("marshal presentation request: %w", err)
		}
		body = bytes.NewReader(raw)
	}

	request, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return fmt.Errorf("create presentation request: %w", err)
	}
	if payload != nil {
		request.Header.Set("Content-Type", "application/json")
	}

	response, err := s.httpClient.Do(request)
	if err != nil {
		return fmt.Errorf("call presentation: %w", err)
	}
	defer response.Body.Close()

	if response.StatusCode < http.StatusOK || response.StatusCode >= http.StatusMultipleChoices {
		return fmt.Errorf("presentation returned status %d", response.StatusCode)
	}

	if target == nil {
		_, _ = io.Copy(io.Discard, response.Body)
		return nil
	}
	if err := json.NewDecoder(response.Body).Decode(target); err != nil {
		return fmt.Errorf("decode presentation response: %w", err)
	}

	return nil
}
