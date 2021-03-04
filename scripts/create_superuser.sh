#!/bin/bash
# This script can be used to create a superuser in django.
# Pass an argument to set a custom name/password for the superuser.
# Default username and password will be 'superuser'.
if [ -z "$1" ]
  then
    su_username="superuser"
else
  su_username="$1"
fi
user_id=$(id -u)
create_su_shell="from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
get_user_model().objects.filter(username='$su_username').delete()
su = get_user_model().objects.create_superuser('$su_username', '$su_username@example.com', '$su_username')
EmailAddress.objects.filter(email=su.email).delete()
EmailAddress.objects.create(user=su, email=su.email, verified=True, primary=True)"
echo "$create_su_shell" | docker-compose run -u "$user_id" --rm web python manage.py shell
echo "Created superuser with username and password: $su_username"
