#!/usr/bin/env bash

for app in uploads teams participants pages evaluation challenges profiles jqfileupload
do
    python manage.py migrate --fake $app zero
    find . -path "./$app/migrations/*.py" -not -name "__init__.py" -delete
    find . -path "./$app/migrations/*.pyc"  -delete
done

python manage.py makemigrations
python manage.py migrate --fake-initial
