import datetime
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.template.loader import get_template

from ladder.models import Season, LadderSubscription
from tennis.settings import SUBSCRIPTION_EMAIL


def send_ladder_emails():
    # search current season ladders that have result in last 24 hours
    season = Season.objects.latest('start_date')
    print(season)
    ladders = season.ladder_set.all()

    # iterate through subscriptions and send email
    for ladder in ladders:
        print(ladder)

        # check ladder has results
        date_from = datetime.datetime.now() - datetime.timedelta(days=1)
        if ladder.result_set.filter(date_added__gte=date_from).count() == 0:
            print('No results in past day')
            continue

        subscriptions = ladder.laddersubscription_set.all()
        for subscription in subscriptions:
            print(subscription)

            # using https://github.com/leemunroe/responsive-html-email-template
            message = get_template("ladder/ladder/subscription/email.html").render({
                'ladder': ladder,
                'user': subscription.user,
                'protocol': 'https',
                'domain': 'highgate-ladder.co.uk' # todo: use use site framework to do these
            })

            mail = EmailMessage(
                subject=ladder.__str__() + " Result Update",
                body=message,
                from_email=SUBSCRIPTION_EMAIL,
                to=[subscription.user.email],
                reply_to=[SUBSCRIPTION_EMAIL],
            )
            mail.content_subtype = "html"
            mail.send()

    return


class Command(BaseCommand):
    help = 'Sends subscription emails'

    def handle(self, *args, **options):
        send_ladder_emails()

