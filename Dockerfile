FROM python:2.7

# Stream logs instead of buffer
ENV PYTHONUNBUFFERED 1

# https://github.com/DefectDojo/django-DefectDojo/issues/407#issuecomment-415862064
RUN sed '/st_mysql_options options;/a unsigned int reconnect;' /usr/include/mysql/mysql.h -i.bkp

RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
ADD . /code/