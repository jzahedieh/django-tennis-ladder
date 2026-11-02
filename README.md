# Highgate Tennis Ladder (`django-tennis-ladder`)

[![CI](https://github.com/jzahedieh/django-tennis-ladder/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/jzahedieh/django-tennis-ladder/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-092E20.svg)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Site](https://img.shields.io/badge/live-highgate--ladder.co.uk-brightgreen)](https://highgate-ladder.co.uk/)

An online league and ladder management application built with Django to track seasonal divisions, match results, head-to-head records, and club statistics for Highgate Cricket & Lawn Tennis Club.

**Live at:** [https://highgate-ladder.co.uk/](https://highgate-ladder.co.uk/)

---

## Features

- **Seasons & Divisions:** Organise multi-division round-robin ladders across seasonal rounds (including draft seasons before publication).
- **Match Result Entry:** Authenticated players can log, edit, and manage their own division match scores online.
- **Head-to-Head & Player Profiles:** View historical performance across seasons, centile rankings, and head-to-head match history between any two players.
- **Club Statistics & Leaderboards:** Track season progress, completion rates, recent results, and all-time club leaderboards.
- **Email Notifications:** Daily digest emails for subscribed players when new results are posted in their division, with one-click token unsubscribe.
- **Spreadsheet Import/Export & REST API:** Management commands for importing/exporting season spreadsheets (`.xlsx` / `.xls`) and a read-only Django REST Framework API.

## Tech Stack

- **Backend:** Python 3.12+, Django 5.2, Django REST Framework
- **Database:** MySQL 8
- **Static Files & Server:** WhiteNoise, Gunicorn, Nginx
- **Environment:** Docker & Docker Compose

## Quick Start (Local Development)

### Using Docker Compose

1. Start the development stack (uses environment variables in `.env.dev`):
   ```bash
   docker compose up -d
   ```
   - **Web App:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
   - **Adminer (MySQL UI):** [http://127.0.0.1:8001/](http://127.0.0.1:8001/)
   - **MailHog (Email testing):** [http://127.0.0.1:8002/](http://127.0.0.1:8002/)

2. Run database migrations and create an admin user:
   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py createsuperuser
   ```

### Running Tests

With Docker Compose:
```bash
docker compose exec web python manage.py test ladder
```

Or with a local virtual environment (configured via `.env.local`):
```bash
./venv/bin/python manage.py test ladder
```

## Contributing & Issues

- **Bug Reports & Feature Requests:** Please open an issue on the [GitHub Issue Tracker](https://github.com/jzahedieh/django-tennis-ladder/issues).
- **Pull Requests:** Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Released under the [MIT License](LICENSE).
