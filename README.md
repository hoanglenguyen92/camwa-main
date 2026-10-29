# camwa-main

FastAPI backend for CAMWA. Keycloak (realm `camwa`) owns accounts, passwords and roles. The backend is its only client: it signs users in, checks Keycloak's tokens on every call, and decides access per endpoint. [docs/keycloak-auth-design.md](docs/keycloak-auth-design.md) describes the design.

## Run locally

You need Docker, Python 3.13 and GNU Make. Docker runs the app database, the Keycloak database and Keycloak. The backend runs on the host.

1. Create `.env` with generated secrets, and install the backend into `.venv`:

   ```
   make env
   make install
   ```

   Fill in the `MAIL_*` values in `.env` if you want Keycloak to send set-password and reset emails. Everything else works without them.

2. Start the stack and seed it:

   ```
   make start
   ```

   This starts the containers, seeds reference data, and runs the backend with reload. The API docs are at http://localhost:8000/docs.

3. Sign in with `POST /api/v1/auth/login` as the CAMWA admin. The email is `SEED_ADMIN_EMAIL` and the password is `SEED_ADMIN_PASSWORD` in `.env`.

Run `make seed-demo` to add one FA, LECTURER, AC and STUDENT account in program CSE (`demo.fa@example.com` and so on), with password `SEED_DEMO_PASSWORD`. Run `make` on its own to list every target.

| Service | Address | Notes |
|---|---|---|
| Backend | http://localhost:8000 | `make run` |
| Keycloak console | http://localhost:8080/admin | User `KC_BOOTSTRAP_ADMIN_USERNAME`. Realm `camwa`. |
| App database | localhost:5432 | Database and user `camwa`. `make psql` |

Keycloak imports `keycloak/realm-camwa.json` only when its database is empty. After you change that file, run `make reset` and `make start`. `make reset` deletes both databases.

## Accounts

An admin adds accounts in the Keycloak console, with the CAMWA id as the username, or uploads a CSV to `POST /api/v1/users/imports`. The CSV columns are `camwa_id,email,first_name,last_name,role,program_id,intake,phone_number`. `PATCH /api/v1/users/{camwa_id}` with `{"active": false}` deactivates an account and ends its sessions.

## Migrating an existing database

`init_db` uses `create_all`, which never alters existing tables. Apply the files in `docs/migrations/` in order. For a database that still has the `iam` table, back it up and then:

1. Run step 1 of `003_keycloak_user_store.sql`.
2. Run `python -m scripts.export_iam_csv > users.csv`, and upload `users.csv` to `POST /api/v1/users/imports` as an admin.
3. Run `python -m scripts.reconcile_users` until it lists no missing accounts.
4. Run step 2 of `003_keycloak_user_store.sql`, which drops `iam`.

Imported users set a password from the email Keycloak sends, or with `POST /api/v1/auth/password-reset`.
## TypeScript API client

The backend's OpenAPI schema drives a generated TypeScript client in `frontend/src/generated/`. The generator is [Hey API](https://heyapi.dev) (`@hey-api/openapi-ts`). Each backend controller becomes a class, and each of its endpoints becomes a typed static method named after the handler. For example, `StudentsController.getStudent(...)` calls `GET /api/v1/students/{student_id}`. The backend's operation IDs (`<Tag>.<handler>`, set in `main.py`) drive this grouping.

Regenerate the client after you change a route or schema with `make openapi`, or by hand with the backend venv active:

```bash
cd frontend
npm install
npm run gen:api
```

`gen:api` runs two steps. You can also run them separately:

1. `npm run openapi:export` runs `python -m scripts.export_openapi` and writes `frontend/openapi.json`. It needs no `.env`, database, or Keycloak.
2. `npm run openapi:generate` reads `openapi.json` and rewrites `src/generated/`.

Commit `openapi.json` and `src/generated/` together with the backend change, so the diff shows the API change. Do not edit files in `src/generated/` by hand. The next run overwrites them.

Set the base URL once in the frontend app:

```ts
import { client } from './generated/client.gen';

client.setConfig({ baseUrl: 'http://localhost:8000' });
```

Call endpoints through their controller:

```ts
import { AuthenticationController, StudentsController } from './generated';

const { data: tokens } = await AuthenticationController.login({
  body: { email: 'admin@example.com', password: '...' },
});

const { data: student } = await StudentsController.getStudent({
  path: { student_id: '10421002' },
});
```

The client uses the `fetch`, `URLSearchParams.entries`, and iterable DOM types. A future `tsconfig.json` needs `"lib": ["ES2022", "DOM", "DOM.Iterable"]`.
