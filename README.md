# camwa-main

FastAPI backend for CAMWA. Firebase Authentication owns identities and credentials. The `iam` table owns the profile and role, linked by `iam.firebase_uid`. After a Firebase identity is proven, the API issues its own access and refresh JWTs.

## Setup

1. Create a virtual environment and install dependencies:

   ```
   python -m venv .venv
   .venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in the values.

3. Configure Firebase in the [Firebase console](https://console.firebase.google.com):
   1. Authentication > Sign-in method: enable **Email/Password** and **Phone**.
   2. Project settings > Service accounts > **Generate new private key**. Create the `secrets/` directory (it is git-ignored) and save the file as `secrets/firebase-service-account.json`.
   3. Project settings > General > copy the **Web API Key** into `FIREBASE_WEB_API_KEY`.

4. Create the admin account (sets up seed data and a Firebase user for `admin@example.com`):

   ```
   set SEED_ADMIN_PASSWORD=...   # Linux/macOS: export SEED_ADMIN_PASSWORD=...
   python seed.py
   ```

5. Run the API:

   ```
   uvicorn main:app --reload
   ```

## Migrating an existing database

`init_db` uses `create_all`, which never alters existing tables. Apply `docs/migrations/001_firebase_auth.sql` to Postgres in two steps:

1. Run step 1 of the SQL file (adds `firebase_uid` and `phone_number`, relaxes `password`).
2. Run `python -m scripts.migrate_iam_to_firebase`. It links each `iam` row to the Firebase user with the same email, or creates one without a password. It is safe to rerun.
3. Run step 2 of the SQL file (makes `firebase_uid` NOT NULL and drops `password`, `failed_attempts`, `locked_until`, `last_attempt_at`).

Argon2 hashes cannot be imported into Firebase. Users created by the script must set a password with `POST /api/auth/forgot-password` before they can log in with email and password.

Users imported from Excel without a password column value are created without a password. They set one via `POST /api/auth/forgot-password`.

## Login flows

Both flows return the same token payload.

**Email and password.** `POST /api/auth/login` with `{"email", "password"}`. The API verifies the credentials with Firebase and issues JWTs.

**Phone OTP.** The client signs in with the Firebase JS or mobile SDK (`signInWithPhoneNumber` plus reCAPTCHA), gets an ID token, and sends `POST /api/auth/firebase-login` with `{"id_token"}`. The same endpoint accepts an ID token from any client-side Firebase sign-in.

Phone login works only for users whose `phone_number` was set on their account (`POST /api/account/create` or `PUT /api/account/{iam_id}`), because that sets the phone number on the same Firebase user. A phone number with no matching account returns 403.

`POST /api/auth/forgot-password` with `{"email"}` sends a Firebase password reset email. It returns the same response whether or not the account exists.
