# Upgrade Plan

Upgrade plan and place to document any changes

## Django 1.9 - 1.11.29 [&check;]

First step get to 1.11 LTS

### Notices

```
?: (mysql.W002) MySQL Strict Mode is not set for database connection 'default'
	HINT: MySQL's Strict Mode fixes many data integrity problems in MySQL, such as data truncation upon insertion, by escalating warnings into errors. It is strongly recommended you activate it. See: https://docs.djangoproject.com/en/1.11/ref/databases/#mysql-sql-mode
```

To pick up at later date

## Python 2 - 3.7 [&check;]

Upgrade to Python 3.7 as 3.8 is not supported in 1.11.29

* TravisCI &check;
* MySQL-Python - mysqlclient &check;

## Move to cloud [&check;]

The current deployment process with django europe is very manual,
in order to upgrade and maintain the project the plan is to move
to Digital Ocean using docker-compose with production configuration:

* mariadb
* adminer
  * [with login](https://www.adminer.org/en/extension/)
* python
  * with gunicorn
* nginx
* certbot

## Django 1.11 - 2.2.11 [&check;]

Upgrade to 2.2 LTS

## Python 3.7 - 3.8 [&check;]

Upgrade to latest Python 3

## Django 2.2 - 3.0 [&check;]

Upgrade to latest 3.0

## Django Rest Framework

Longer term plan is to use DRF to create an API to replace the frontend