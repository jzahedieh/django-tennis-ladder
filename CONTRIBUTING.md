# Contribution Guidelines

Welcome! It is **awesome** to have you here. Feel free to get in touch about anything or open an issue—we look forward to reviewing your pull request!

## Getting a Development Environment

[Docker Compose](https://docs.docker.com/compose/) is used for both local development and production environments:

* `docker compose up -d` will start the development environment with the environment variables defined in `.env.dev`:
  * **Django web app:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
  * **Adminer (MySQL database UI):** [http://127.0.0.1:8001/](http://127.0.0.1:8001/) *(see `.env.dev` for login details)*
  * **MailHog (captured emails):** [http://127.0.0.1:8002/](http://127.0.0.1:8002/)
* Run `docker compose exec web python manage.py migrate` to apply migrations and seed initial data.
* Run `docker compose exec web python manage.py createsuperuser` to create an admin user.

## Running the Test Suite

Before submitting a pull request, make sure the test suite and Django checks pass:

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py test ladder
```

*(Or if running with a local virtual environment: `./venv/bin/python manage.py test ladder`)*

## Submitting a Pull Request

1. [Fork](https://github.com/jzahedieh/django-tennis-ladder/fork) and clone the repository.
2. Create a new branch: `git checkout -b my-branch-name`
3. Make your changes and verify tests pass.
4. Push to your fork and [submit a pull request](https://github.com/jzahedieh/django-tennis-ladder/compare).
5. Pat yourself on the back and wait for your pull request to be reviewed and merged!

## Resources

- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [About Pull Requests](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests)
- [GitHub Docs](https://docs.github.com/)
