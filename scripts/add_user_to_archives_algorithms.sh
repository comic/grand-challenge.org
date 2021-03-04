#!/bin/bash
# This script is used to add a user as a user all existing archives and algorithms.
# Pass the username of the user as argument
if [ -z "$1" ]
  then
    echo "Error, no arguments. Pass username to be added to archives and algorithms as argument."
    exit 1
fi
user_id=$(id -u)
add_user_cmd="from django.contrib.auth import get_user_model
from grandchallenge.algorithms.models import Algorithm
from grandchallenge.archives.models import Archive
u = get_user_model().objects.filter(username='$1').get()
for model in (Archive, Algorithm):
    for obj in model.objects.all():
        obj.add_user(u)"
echo "$add_user_cmd" | docker-compose run -u "$user_id" --rm web python manage.py shell
echo "Added user $1 as a user of all existing archives and algorithms"
