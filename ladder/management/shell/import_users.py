from django.contrib.auth.models import User, Group
from ladder.models import Player
import uuid

# python manage.py shell < ladder/management/shell/import_users.py
# format first_name, last_name, email
players = [
    ["John", "Doe", "jo@hn.doe"],
]

group_object = Group.objects.get(name='player')

for player in players:
    first_name = player[0]
    last_name = player[1]
    email = player[2]

    if not email:
        print(first_name + " " + last_name + ": No Email")
        continue

    if User.objects.filter(username=email).exists():
        user_object = User.objects.get_by_natural_key(email)
    else:
        user_object = User(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_staff=False,
            is_superuser=False
        )
        user_object.set_password(uuid.uuid4().hex)
        user_object.save()

    user_object.groups.add(group_object)
    user_object.save()

    try:
        player_object = Player.objects.get(first_name=first_name, last_name=last_name)
        player_object.user = user_object
        player_object.save()
        print(first_name + " " + last_name + " " + email + ": Linked")
    except Player.DoesNotExist:
        print(first_name + " " + last_name + " " + email + ": No Player")
