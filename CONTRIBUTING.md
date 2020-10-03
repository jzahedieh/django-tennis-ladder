# Contribution Guidelines

Welcome hackers it is really **awesome** have you here! This is an old project and as such the frontend is fairly outdated,
feel free to get in contact about anything and look forward to reviewing your pull request :)

## Getting a development environment

[Docker Compose](https://docs.docker.com/compose/) is used for both local development and live environments

* `docker-composer up -d` will start the development environment with the environment variables defined in `.env.dev`
    * django / web will be available @ http://127.0.0.1:8000/
    * adminer for viewing the MySQL database is available @ http://127.0.0.1:8001/ _(see `.env.dev` for login details)_
    * mailhog for viewing sent emails is available @ http://127.0.0.1:8002/
* Run `docker-compose exec web python manage.py migrate` to install with seeded data
* Run `docker-compose exec web python manage.py createsuperuser` to create an admin user

## Submitting a pull request

1. [Fork](https://github.com/jzahedieh/django-tennis-ladder/fork) and clone the repository
1. Create a new branch: `git checkout -b my-branch-name`
1. Push to your fork and [submit a pull request](https://github.com/jzahedieh/django-tennis-ladder/compare)
1. Pat your self on the back and wait for your pull request to be reviewed and merged.

## Resources

- [How to Contribute to Open Source](https://opensource.guide/how-to-contribute/)
- [Using Pull Requests](https://help.github.com/articles/about-pull-requests/)
- [GitHub Help](https://help.github.com)
