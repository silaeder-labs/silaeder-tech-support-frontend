# AGENTS.md

Instructions for AI coding agents working in this repository.

This repository uses a Vue.js + TypeScript + shadcn-vue frontend and a Go backend built with Echo, pgx, Goose, and PostgreSQL.

AGENTS.md is standard Markdown. Keep this file practical, current, and focused on instructions that help an agent make safe changes without guessing.

## Scope and precedence

- This file applies to the whole repository unless a more specific `AGENTS.md` exists in a subdirectory.
- When working in a nested directory, read the closest `AGENTS.md` first and treat it as more specific than this root file.
- Explicit user instructions in the current task override this file.
- Do not follow stale comments, examples, or generated code when they conflict with the current source code.
- If an instruction in this file conflicts with the existing project configuration, prefer the actual checked-in configuration and mention the conflict in your final response.

## Agent operating rules

- Make the smallest correct change that satisfies the task.
- Preserve existing architecture, naming, file layout, public APIs, and dependency choices unless the task explicitly asks for a change.
- Read nearby files before editing. Match local patterns over generic best practices.
- Do not introduce a new framework, package manager, state library, router, validator, ORM, query builder, migration tool, logger, or UI kit unless explicitly requested.
- Do not change major dependency versions without an explicit request.
- Do not commit secrets, `.env` files, private keys, tokens, credentials, production dumps, or real user data.
- Do not leave temporary debug code: `console.log`, `debugger`, `fmt.Println`, commented-out code, unused files, or placeholder TODOs.
- Do not silently skip tests or type checks. If a check cannot run, explain exactly why.
- Prefer boring, readable, maintainable code over clever abstractions.

## Repository discovery checklist

Before making changes, inspect the relevant project files:

- Root: `README.md`, `AGENTS.md`, `Makefile`, `Taskfile.yml`, `justfile`, `.github/workflows/*`, `docker-compose.yml`.
- Frontend: `frontend/package.json`, lockfile, `vite.config.*`, `tsconfig*.json`, `components.json`, Tailwind config, existing component patterns.
- Backend: `backend/go.mod`, `backend/go.sum`, route registration, config loading, existing handlers, services, repositories, migrations.
- Database: `backend/migrations/*`, schema conventions, existing indexes, constraints, and rollback patterns.

Use actual scripts and commands from the repository when they exist. The commands below are defaults only.

## Default commands

### Frontend

Use the existing package manager. Detect it from the lockfile:

- `pnpm-lock.yaml` -> `pnpm`
- `package-lock.json` -> `npm`
- `yarn.lock` -> `yarn`
- `bun.lockb` or `bun.lock` -> `bun`

Typical commands:

```bash
cd frontend
pnpm install
pnpm dev
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

If the project has different script names, use the scripts in `package.json`.

### Backend

Typical commands:

```bash
cd backend
go mod download
gofmt -w <changed-go-files>
go test ./...
go vet ./...
go run ./cmd/api
```

If the repository has `make test`, `make lint`, `task test`, `just test`, `golangci-lint`, or `staticcheck`, prefer the project-defined command.

### Database migrations

Typical Goose commands:

```bash
cd backend
goose -dir ./migrations postgres "$DATABASE_URL" status
goose -dir ./migrations postgres "$DATABASE_URL" create add_example_table sql
goose -dir ./migrations postgres "$DATABASE_URL" up
goose -dir ./migrations postgres "$DATABASE_URL" down
```

Environment-variable style is also acceptable if the project already uses it:

```bash
export GOOSE_DRIVER=postgres
export GOOSE_DBSTRING="$DATABASE_URL"
export GOOSE_MIGRATION_DIR=./migrations
goose status
goose up
```

Never run destructive migration commands such as `reset`, `down-to 0`, broad `DROP`, `TRUNCATE`, or irreversible data migrations unless the user explicitly asks for it.

## Frontend rules: Vue.js + TypeScript

### Vue style

- Use Vue 3 Single File Components.
- New Vue components should use `<script setup lang="ts">` unless the surrounding file pattern requires otherwise.
- Prefer the Composition API for new code.
- Keep templates declarative. Move non-trivial conditions, mapping, and derived values into `computed` or helper functions.
- Do not mutate props directly.
- Use `computed` for derived state and `watch` only for side effects, async synchronization, URL synchronization, or integration with external APIs.
- Avoid direct DOM manipulation. Use template refs only when needed for focus, measurements, or third-party integrations.
- Keep component state as local as possible. Use global stores only for genuinely shared application state.

Example component shape:

```vue
<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  title: string
  count?: number
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  count: 0,
  disabled: false,
})

const emit = defineEmits<{
  select: [id: string]
}>()

const label = computed(() => `${props.title} (${props.count})`)

function handleSelect(id: string) {
  if (props.disabled) return
  emit('select', id)
}
</script>

<template>
  <button type="button" :disabled="disabled" @click="handleSelect('current')">
    {{ label }}
  </button>
</template>
```

### TypeScript rules

- Keep TypeScript strict. Do not weaken `tsconfig` strictness to make code pass.
- Avoid `any`. If unavoidable at an external boundary, keep it local and convert to a typed shape immediately.
- Use `import type` for type-only imports.
- Prefer explicit interfaces for request DTOs, response DTOs, component props, emitted events, and domain view models.
- Distinguish optional and nullable values:
  - `field?: T` means the field may be absent.
  - `field: T | null` means the field is present but may be null.
- Do not use broad type assertions such as `as unknown as T` unless there is no safe alternative.
- Do not duplicate backend contracts manually if the project already has generated API types or shared schemas.

### API client rules

- Keep HTTP calls in `src/api`, a feature-level API module, or the existing project location.
- Do not scatter raw `fetch` or `axios` calls throughout components if a shared client exists.
- Type all request payloads and responses.
- Treat backend responses as untrusted at the boundary.
- Handle loading, success, empty, and error states in UI flows.
- Never show raw SQL errors, stack traces, panic messages, or internal backend details to users.
- Use existing auth token, refresh, retry, and error handling conventions.

### Composables

- Name composables `useSomething`.
- Keep composables focused on one responsibility.
- Return explicit refs, computed values, and functions.
- Avoid hidden global side effects unless the composable name clearly communicates them.
- For async composables, follow the existing project pattern for `data`, `error`, `isLoading`, `execute`, `reload`, or cancellation.

## Frontend UI rules: shadcn-vue

### Correct library

- Use `shadcn-vue`, not React `shadcn/ui`.
- Do not add React-only shadcn dependencies such as `@radix-ui/react-*` or `lucide-react` to the Vue app.
- Use the project's existing shadcn-vue component layout and `components.json` configuration.
- Treat shadcn-vue components as editable local source once they are added to the repo, but preserve their public API unless there is a good reason to change it.

### Component organization

- Base UI primitives belong in `src/components/ui` or the existing shadcn-vue path.
- Product-specific components belong in `src/components`, `src/components/app`, `src/features/<feature>/components`, or the existing project convention.
- Do not put business logic into generic UI primitives.
- Prefer wrappers or feature components over modifying a shared primitive for one page-specific use case.

### Tailwind and styling

- Use Tailwind utilities and existing design tokens.
- Use the project's `cn()` helper when composing conditional class names.
- Do not add global CSS overrides when props, classes, variants, or wrappers can solve the problem.
- Do not inline styles except for runtime CSS variables, measured values, or third-party integration requirements.
- Keep responsive states, focus states, hover states, disabled states, and dark mode behavior consistent with existing UI.

Example wrapper:

```vue
<script setup lang="ts">
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  active?: boolean
}

defineProps<Props>()
</script>

<template>
  <Button :class="cn('w-full justify-start', active && 'bg-muted')">
    <slot />
  </Button>
</template>
```

### Accessibility

- All interactive elements must be keyboard accessible.
- Icon-only buttons need an accessible label.
- Inputs need labels or equivalent accessible names.
- Preserve visible focus styles.
- Prefer shadcn-vue primitives for dialog, dropdown, popover, select, tooltip, and command menu behavior.
- Validation errors should be visible, understandable, and associated with the relevant field.

## Backend rules: Go

### General Go style

- Write idiomatic Go.
- Always run `gofmt` on changed Go files.
- Pass `context.Context` through HTTP, service, repository, database, and external-service calls.
- Do not ignore errors. If an error is intentionally ignored, make the reason obvious.
- Use `%w` when wrapping errors that callers may need to inspect.
- Do not panic in request-handling paths.
- Avoid package-level mutable state.
- Do not start goroutines without cancellation, error handling, and lifecycle ownership.
- Keep interfaces small and define them at the consumer side when practical.

### Backend layering

Use the existing architecture. If no clear architecture exists, follow this separation:

- `cmd/api`: process entrypoint and dependency wiring.
- `internal/config`: environment and configuration parsing.
- `internal/db`: pgxpool setup, database health checks, transaction helpers.
- `internal/domain`: domain entities, value objects, and domain errors.
- `internal/repository`: SQL queries and row mapping.
- `internal/service`: business logic, authorization decisions, transactions.
- `internal/http` or `internal/handler`: Echo routes, request DTOs, response DTOs, HTTP error mapping.

Handlers must not contain SQL. Repositories must not import Echo. Services should not depend on HTTP DTOs.

## Backend HTTP rules: Echo

### Echo version

Before editing Echo code, inspect `go.mod`:

- If the module imports `github.com/labstack/echo/v4`, use Echo v4 APIs and patterns.
- If the module imports `github.com/labstack/echo/v5`, use Echo v5 APIs and patterns.
- Do not migrate between Echo major versions unless explicitly requested.

### Routes

- Register routes in the existing central route registration location.
- Group API routes by version when the project does so, for example `/api/v1`.
- Use consistent REST-style paths: `/users`, `/users/:id`, `/projects/:projectID`.
- Apply middleware at the narrowest correct scope: global, group, or route.
- Keep route registration separate from business logic.

Example for Echo v4:

```go
func RegisterRoutes(e *echo.Echo, h *Handler, auth echo.MiddlewareFunc) {
	api := e.Group("/api/v1")
	api.GET("/health", h.Health)

	users := api.Group("/users", auth)
	users.POST("", h.CreateUser)
	users.GET("/:id", h.GetUser)
}
```

### Handlers

Handlers should do only HTTP work:

1. Read path, query, header, and body input.
2. Bind JSON into request DTOs.
3. Validate request DTOs.
4. Convert request DTOs to service inputs.
5. Call service methods with `c.Request().Context()`.
6. Convert service outputs to response DTOs.
7. Return JSON with the correct HTTP status.

Example for Echo v4:

```go
type createUserRequest struct {
	Email string `json:"email" validate:"required,email"`
	Name  string `json:"name" validate:"required,min=1,max=120"`
}

type userResponse struct {
	ID    string `json:"id"`
	Email string `json:"email"`
	Name  string `json:"name"`
}

func (h *Handler) CreateUser(c echo.Context) error {
	var req createUserRequest
	if err := c.Bind(&req); err != nil {
		return err
	}
	if err := c.Validate(&req); err != nil {
		return err
	}

	user, err := h.users.Create(c.Request().Context(), service.CreateUserInput{
		Email: req.Email,
		Name:  req.Name,
	})
	if err != nil {
		return err
	}

	return c.JSON(http.StatusCreated, userResponse{
		ID:    user.ID.String(),
		Email: user.Email,
		Name:  user.Name,
	})
}
```

### Binding and validation

- Binding is not validation. Bind first, then validate.
- Use request-specific DTOs instead of binding directly into domain models.
- Never trust client-provided fields such as `id`, `role`, `is_admin`, `created_at`, `updated_at`, `tenant_id`, or ownership fields.
- Use the existing validator setup. If the project uses `go-playground/validator`, follow its tag style.
- Map validation errors to a consistent response shape.

### HTTP errors

- Use one consistent JSON error format.
- Do not expose stack traces, SQL details, internal package names, or panic text to clients.
- Map domain errors to HTTP statuses in one place when possible.
- Use correct status codes:
  - `200 OK` for successful reads and updates with response body.
  - `201 Created` for successful creates.
  - `204 No Content` for successful deletes or updates without response body.
  - `400 Bad Request` for malformed input.
  - `401 Unauthorized` for missing or invalid authentication.
  - `403 Forbidden` for authenticated users without permission.
  - `404 Not Found` for missing resources.
  - `409 Conflict` for uniqueness or state conflicts.
  - `422 Unprocessable Entity` for semantic validation errors if the project uses it.
  - `500 Internal Server Error` for unexpected server errors.

Example error response shape:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Validation failed",
    "details": []
  }
}
```

## Backend database rules: pgx + PostgreSQL

### pgx usage

- Use `pgxpool.Pool` for the application database pool.
- Do not use a single global `pgx.Conn` for a concurrent HTTP server.
- Create the pool during application startup and close it during graceful shutdown.
- Read database connection settings from configuration, not hardcoded strings.
- Pass context to every database call.

Example pool setup:

```go
func NewPool(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("parse postgres config: %w", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("create postgres pool: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}

	return pool, nil
}
```

### SQL rules

- Use PostgreSQL positional parameters: `$1`, `$2`, `$3`.
- Never concatenate user input into SQL strings.
- For dynamic identifiers such as sort columns, use an allowlist.
- Keep SQL near repositories unless the project uses `.sql` files or generated queries.
- Use explicit column lists. Avoid `SELECT *` in application queries.
- Call `defer rows.Close()` after successful `Query`.
- Check `rows.Err()` after iterating.
- Convert `pgx.ErrNoRows` into a domain-level not-found error.
- Do not leak raw database errors to HTTP responses.

Example repository method:

```go
func (r *UserRepository) GetByID(ctx context.Context, id uuid.UUID) (domain.User, error) {
	const q = `
		SELECT id, email, name, created_at, updated_at
		FROM users
		WHERE id = $1
	`

	var u domain.User
	err := r.db.QueryRow(ctx, q, id).Scan(
		&u.ID,
		&u.Email,
		&u.Name,
		&u.CreatedAt,
		&u.UpdatedAt,
	)
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.User{}, domain.ErrUserNotFound
	}
	if err != nil {
		return domain.User{}, fmt.Errorf("get user by id: %w", err)
	}

	return u, nil
}
```

### Transactions

- Start transactions in the service layer for operations that must be atomic.
- Always use `defer tx.Rollback(ctx)` after beginning a transaction.
- Commit only after all operations succeed.
- Do not keep a transaction open during external network calls or long-running work.
- If repositories need to work with both pool and transaction, use a small shared interface.

Example shared query interface:

```go
type Querier interface {
	Exec(ctx context.Context, sql string, arguments ...any) (pgconn.CommandTag, error)
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
	QueryRow(ctx context.Context, sql string, args ...any) pgx.Row
}
```

## Database migrations: Goose

### Migration rules

- Every schema change must be represented as a Goose migration.
- Prefer SQL migrations unless the project already uses Go migrations for a specific reason.
- Do not edit migrations that may already have been applied in shared, staging, or production environments.
- Create a new migration for follow-up changes.
- Use one migration per logical schema change.
- Include `-- +goose Up` and `-- +goose Down` sections whenever possible.
- Use `-- +goose StatementBegin` and `-- +goose StatementEnd` around PostgreSQL functions, triggers, or multi-statement blocks that Goose must treat as one statement.
- Use `-- +goose NO TRANSACTION` only when PostgreSQL requires it, such as certain concurrent index operations.
- Do not perform destructive data migrations without explicit approval.

Example migration:

```sql
-- +goose Up
CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text NOT NULL UNIQUE,
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- +goose Down
DROP TABLE users;
```

### PostgreSQL schema conventions

- Follow the existing project convention for primary keys: UUID, identity, bigserial, or another style.
- Prefer `timestamptz` for timestamps.
- Add `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys, and indexes when they represent real invariants or query needs.
- Do not add indexes blindly. Add them for actual lookup, join, filter, or ordering patterns.
- Use `text` unless the project has a reason for length-limited `varchar(n)`.
- Use `numeric` or integer minor units for money. Do not use floating-point types for money.
- For status fields, follow the project convention: PostgreSQL enum, text + check constraint, lookup table, or application enum.

### Safe migration pattern for large tables

For existing large tables, avoid long locks and unsafe rewrites:

1. Add nullable columns first.
2. Backfill data separately, preferably in batches if the table is large.
3. Add defaults for new rows.
4. Add constraints as `NOT VALID` when appropriate.
5. Validate constraints separately.
6. Add `NOT NULL` only after data is valid.

Do not add a required column with an expensive default to a large production table without considering lock behavior.

## API contract between frontend and backend

- Backend DTOs define the API contract.
- Frontend request and response types must match the backend contract.
- If the project uses OpenAPI, generated clients, shared schemas, or typed SDKs, update generated artifacts when the contract changes.
- Do not rename, remove, or change response fields without checking all frontend usages.
- Use ISO 8601 / RFC3339 strings for timestamps in JSON.
- Do not send money as JSON floats.
- Keep error response shapes stable so the frontend can handle them predictably.

## Testing requirements

### Frontend tests

- Test user-visible behavior, not implementation details.
- Cover loading, empty, success, and error states where relevant.
- For forms, test validation messages and submit-disabled behavior.
- Prefer role and label based queries in UI tests.
- Avoid snapshot-only tests for important behavior.

### Backend tests

- Use table-driven tests for services, validators, and pure functions.
- Test handlers for status code, response body, and error mapping.
- Repository tests should use the existing integration test setup if available.
- Do not make tests depend on real external services unless the repository already has that convention.
- Use fakes or mocks at service boundaries where appropriate.

### Migration checks

When changing migrations and a database is available:

```bash
goose -dir ./migrations postgres "$DATABASE_URL" status
goose -dir ./migrations postgres "$DATABASE_URL" up
goose -dir ./migrations postgres "$DATABASE_URL" status
```

If the migration has a meaningful `Down`, test one rollback in a disposable database.

## Security rules

- Validate input on the backend even when the frontend validates it.
- Use parameterized SQL for all user input.
- Use allowlists for dynamic SQL identifiers.
- Do not log secrets, passwords, auth headers, cookies, tokens, refresh tokens, private keys, or full request bodies containing sensitive data.
- Do not expose internal errors to clients.
- Keep CORS explicit. Do not use wildcard origins with credentials.
- Enforce authorization on the backend for every protected operation.
- Do not trust client-provided ownership, role, tenant, or admin fields.
- Use secure cookie settings if the project uses cookies: `HttpOnly`, `Secure`, and appropriate `SameSite`.

## Logging and observability

- Use the existing logger and log format.
- Prefer structured logs for backend code.
- Include request IDs or correlation IDs when available.
- Log unexpected server errors once at the boundary. Avoid duplicate logs at every layer.
- Health endpoints should be cheap. Readiness endpoints may check PostgreSQL connectivity.

## Performance rules

### Frontend

- Avoid unnecessary API calls during render cycles.
- Avoid heavy computations in templates.
- Paginate or virtualize large lists when needed.
- Do not add large client dependencies for small utilities.
- Keep bundle impact in mind when adding UI, date, chart, editor, or validation libraries.

### Backend

- Avoid N+1 queries.
- Use pagination for list endpoints.
- Use explicit limits for potentially large result sets.
- Do not load entire large tables into memory.
- Add indexes for real query patterns, not speculation.
- Do not hold database connections longer than necessary.

## Configuration rules

- Read runtime configuration from environment variables, config files, or the existing project config system.
- Parse and validate config at startup.
- Do not read environment variables deep inside handlers or services.
- Frontend environment variables must be safe to expose to the browser. For Vite, only expose intended `VITE_*` variables.
- Keep `.env.example` updated when adding required configuration.

## Documentation rules

Update documentation when behavior changes:

- API endpoints or response shapes.
- Required environment variables.
- Setup, build, test, or migration commands.
- Database schema assumptions.
- Feature flags or deployment requirements.

Do not duplicate long README content in AGENTS.md. Keep this file focused on agent execution rules and project conventions.

## Pull request and final response expectations

When finishing a task, report:

- What changed.
- Which files were modified.
- Which checks were run.
- Any checks that could not be run and why.
- Any follow-up risks, migrations, environment changes, or deployment notes.

Before considering the task complete, verify as much as possible:

- Frontend typecheck passes after frontend changes.
- Frontend lint/tests/build pass when relevant.
- Go files are formatted with `gofmt`.
- Backend tests pass after backend changes.
- Goose migrations apply cleanly when migration changes are made.
- No secrets, debug code, temporary files, or unrelated lockfile changes were introduced.

## When to stop and ask before proceeding

Ask for explicit confirmation before:

- Running destructive database operations.
- Deleting user data or production-like data.
- Rotating credentials or changing auth/session behavior.
- Introducing a new major dependency or replacing a core library.
- Changing public API contracts in a breaking way.
- Performing broad refactors unrelated to the requested task.

If the user explicitly requested one of these actions, proceed carefully and document the risk.
