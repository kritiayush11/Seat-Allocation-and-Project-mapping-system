# Project Upgrades & Security Audit Summary

This document summarizes all upgrades, migrations, new features, and security enhancements implemented across the frontend and backend of the **Ethara Seat Allocation & Project Mapping System**.

---

## 1. Frontend Build System & Styling Upgrades

* **Vite to Craco Migration**: Migrated the react-scripts compiler to **Craco (Webpack)**. Exposed standard package configurations in `package.json` and adjusted build parameters to load dynamic PostCSS loaders and `@` path aliases.
* **React 19 & Radix UI**: Upgraded React core to **version 19.0.0** and react-router-dom to **version 7.15.0**. Installed full Radix Primitive components, Framer Motion, and Sonner.
* **Shadcn Color Variable Themes**: Added standard light/dark HSL styling tokens in `src/index.css`. Mapped legacy brand classes (like `ethara-card`, `ethara-input`, and `ethara-btn-primary`) directly to these variable tokens.
* **Dockerfile Paths**: Updated the Docker deployment file to copy files from `/app/build` (instead of `/app/dist`) and passed `--legacy-peer-deps` to handle compilation cleanly.

---

## 2. Public Landing Page & Home View

Implemented the premium public-facing marketing landing page under `/` (moving the main administration panel to `/dashboard` protected behind route authentication):
- **Hero Grid**: Styled gradient fuchsia-to-violet typography (*"Every seat. Every project. One glance."*) with visual glow blurs and background hexagon grid overlays.
- **Interactive Live Snapshot Card**: Displays real-time office capacities alongside an 8x5 grid mockup showing color-coded seat statuses (available, occupied, reserved).
- **Navbar Links**: Integrated header pills (Dashboard, Employees, Seats, Assistant) with dynamic Sign In / Sign Out actions dependent on auth status.

---

## 3. Conversational AI Agent & Memory (LangChain)

Upgraded the rule-based assistant to a fully conversational AI agent utilizing **LangChain** and database query bindings:
- **API Key Compatibility**: Automatically detects and uses **Google Gemini** (`GEMINI_API_KEY`), **xAI Grok** (`GROK_API_KEY` / `XAI_API_KEY`), or **OpenAI** (`OPENAI_API_KEY`) based on `.env` settings.
- **Dynamic Database Tools**: Wrapped SQLAlchemy safe queries into functional tools:
  - `get_employee_seat(email_or_name)`: Gets an employee's seat coordinate and project.
  - `search_seats(floor, zone, status)`: Searches seats matching filters.
  - `get_seat_utilization()`: Dynamic metrics summary.
  - `search_projects(query)`: Search projects.
  - `find_neighbors(email_or_name)`: Spot co-workers in the same zone.
- **In-Database Memory**: Created the `chat_messages` model to persist conversations associated with a unique client `session_id`, making previous context recall possible across multiple request inputs.

---

## 4. NLP Voice Dictation (Speech-to-Text)

- Configured a microphone dictation button (`Mic` / `MicOff`) inside the AI Assistant chat bar.
- Integrates the browser's native **Web Speech API (`webkitSpeechRecognition`)** to transcribe voice commands into text locally without extra latency or API key usage.

---

## 5. Security & Cybersecurity Hardening

Conducted a cybersecurity audit and successfully resolved a critical vulnerability:
- **Leaked JWT Secret Key Fix (TDD)**: The `JWT_SECRET_KEY` defaulted to a static hardcoded key in the repository. We wrote a failing security test case, then patched `get_settings()` inside `config.py` to dynamically execute Python's **Cryptographic Session Generation** (`secrets.token_hex(32)`) on server initialization if the default key is present.
- **AI Query Isolation (Principle of Least Privilege)**: Bounded the LangChain agent's tools to read-only endpoints, entirely separating the LLM model from user login data and password tables to prevent credential leaks via prompt injection.
- **Verified Suite**: All **82 pytest cases passed** cleanly.

---

## 6. Seeded Test Credentials

The database seeding function now automatically provisions the following default credentials:
* **Admin Role**: `admin` / `adminpassword`
* **HR Role**: `hr` / `hrpassword`
* Helper instructions detailing these logins have been placed directly on the login card.

---

## 7. Version Control Protection (.gitignore)

- **Root .gitignore**: Created a comprehensive `.gitignore` file in the project root.
- **Leakage Prevention**: Blocks accidental commitments of local environment files (`.env`), SQLite databases (`ethara_seats.db`, including `-shm` and `-wal` log overlays), python virtual environments (`.venv`), and node packages (`node_modules/`).
