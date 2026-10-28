# camwa-main

FastAPI backend for CAMWA. An external identity provider (Firebase Authentication by default, chosen by `AUTH_PROVIDER`) owns identities and credentials. The `iam` table owns the profile and role, linked by `iam.auth_uid`. After an identity is proven, the API issues its own access and refresh JWTs.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the values.

3. Configure the default provider, Firebase, in the [Firebase console](https://console.firebase.google.com):
   1. Authentication > Sign-in method: enable **Email/Password** and **Phone**.
   2. Project settings > Service accounts > **Generate new private key**. Create the `secrets/` directory (it is git-ignored) and save the file as `secrets/firebase-service-account.json`.
   3. Project settings > General > copy the **Web API Key** into `FIREBASE_WEB_API_KEY`.

4. Create the admin account (sets up seed data and an identity-provider user for `admin@example.com`):

   ```
   set SEED_ADMIN_PASSWORD=...   # Linux/macOS: export SEED_ADMIN_PASSWORD=...
   python seed.py
   ```

5. Run the API:

   ```
   uvicorn main:app --reload
   ```

## Migrating an existing database

`init_db` uses `create_all`, which never alters existing tables. Apply `docs/migrations/001_external_identity.sql` to Postgres in two steps:

1. Run step 1 of the SQL file (adds `auth_uid` and `phone_number`, relaxes `password`).
2. Run `python -m scripts.link_identities`. It links each `iam` row with no `auth_uid` to the provider user with the same email, or creates one without a password. It is safe to rerun.
3. Run step 2 of the SQL file (makes `auth_uid` NOT NULL and drops `password`, `failed_attempts`, `locked_until`, `last_attempt_at`).

Argon2 hashes cannot be imported into Firebase. Users created by the script must set a password with `POST /api/auth/forgot-password` before they can log in with email and password.

Then apply `docs/migrations/002_app_owned_student_ids.sql`. It points `student.student_id` and `image_assets` (column renamed `username` to `iam_id`) at the immutable `iam.iam_id` instead of the editable `iam.username`. Its precheck queries must return no rows first.

Users imported from Excel without a password column value are created without a password. They set one via `POST /api/auth/forgot-password`.

## Login flows

Both flows return the same token payload.

**Email and password.** `POST /api/auth/login` with `{"email", "password"}`. The API verifies the credentials with the identity provider and issues JWTs.

**Phone OTP.** The client signs in with the Firebase JS or mobile SDK (`signInWithPhoneNumber` plus reCAPTCHA), gets an ID token, and sends `POST /api/auth/token-login` with `{"id_token"}`. The same endpoint accepts an ID token from any client-side sign-in the provider verifies.

Phone login works only for users whose `phone_number` was set on their account (`POST /api/account/create` or `PUT /api/account/{iam_id}`), because that sets the phone number on the same provider user. A phone number with no matching account returns 403.

`POST /api/auth/forgot-password` with `{"email"}` sends a password reset email. It returns the same response whether or not the account exists.

## Switching identity provider

1. Implement `IdentityProvider` (`backend/core/identity/base.py`) in `backend/core/identity/<name>.py`. Keep the provider's own settings in that module.
2. Register the class in `PROVIDERS` in `backend/core/identity/__init__.py` and add the name to `AUTH_PROVIDER` in `backend/core/configs.py`.
3. Set `AUTH_PROVIDER=<name>` and the provider's settings in `.env`.
4. Run `python -m scripts.link_identities --relink`. It relinks every `iam` row to the new provider by email, or creates a user without a password. It is safe to rerun.
5. Users set a password with `POST /api/auth/forgot-password`, unless you imported their password hashes into the new provider.

## TypeScript API client

The backend's OpenAPI schema drives a generated TypeScript client in `frontend/src/generated/`. The generator is [Hey API](https://heyapi.dev) (`@hey-api/openapi-ts`). Each endpoint becomes a typed function named after its router tag and handler, for example `authenticationLogin` or `studentGetStudentById`.

Regenerate the client after you change a route or schema. Activate the backend venv first, because the export step runs `python`:

```bash
cd frontend
npm install
npm run gen:api
```

`gen:api` runs two steps. You can also run them separately:

1. `npm run openapi:export` runs `python -m scripts.export_openapi` and writes `frontend/openapi.json`. It needs no `.env`, database, or identity credentials.
2. `npm run openapi:generate` reads `openapi.json` and rewrites `src/generated/`.

Commit `openapi.json` and `src/generated/` together with the backend change, so the diff shows the API change. Do not edit files in `src/generated/` by hand. The next run overwrites them.

Set the base URL once in the frontend app:

```ts
import { client } from './generated/client.gen';

client.setConfig({ baseUrl: 'http://localhost:8000' });
```

The client uses the `fetch`, `URLSearchParams.entries`, and iterable DOM types. A future `tsconfig.json` needs `"lib": ["ES2022", "DOM", "DOM.Iterable"]`.
