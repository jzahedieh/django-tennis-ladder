import datetime
from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.template.loader import get_template

from ladder.models import Season, LadderSubscription
from tennis.settings import SUBSCRIPTION_EMAIL


def send_ladder_emails(days=1, dry_run=False):
    # search current season ladders that have result in last `days`
    season = Season.objects.filter(is_draft=False).latest('start_date')
    print(f"Season: {season}")
    ladders = season.ladder_set.all()

    date_from = datetime.datetime.now() - datetime.timedelta(days=days)

    sent = 0
    skipped = 0

    for ladder in ladders:
        print(f"Checking ladder: {ladder}")

        # check ladder has results in period
        if ladder.result_set.filter(date_added__gte=date_from).count() == 0:
            print("No results in past period")
            skipped += 1
            continue

        subscriptions = ladder.laddersubscription_set.all()
        for subscription in subscriptions:
            unsubscribe_url = f"https://highgate-ladder.co.uk/unsubscribe/{subscription.unsubscribe_token}/"

            message = get_template("ladder/ladder/subscription/email.html").render({
                'ladder': ladder,
                'user': subscription.user,
                'unsubscribe_url': unsubscribe_url,
                'protocol': 'https',
                'domain': 'highgate-ladder.co.uk'
            })

            if dry_run:
                print(f"[DRY-RUN] Would send to {subscription.user.email} for {ladder}")
                sent += 1
                continue

            mail = EmailMessage(
                subject=f"{ladder} Result Update",
                body=message,
                from_email=SUBSCRIPTION_EMAIL,
                to=[subscription.user.email],
                reply_to=[SUBSCRIPTION_EMAIL],
            )
            mail.extra_headers = {
                'List-Unsubscribe': f'<{unsubscribe_url}>',
                'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'
            }
            mail.content_subtype = "html"
            mail.send()
            sent += 1

    print(f"Done. Ladders skipped (no recent results): {skipped}. Emails processed: {sent}.")


class Command(BaseCommand):
    help = "Send ladder email updates to subscribers."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=1,
            help="Look back this many days for results (default: 1)"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not send emails; just print what would be sent."
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        self.stdout.write(f"Sending ladder emails (days={days}, dry_run={dry_run})...")
        send_ladder_emails(days=days, dry_run=dry_run)
        self.stdout.write(self.style.SUCCESS("Finished sending ladder emails."))
