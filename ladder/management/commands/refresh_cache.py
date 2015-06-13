from django.core.management.base import BaseCommand, CommandError
from django.test.client import RequestFactory
from django.conf import settings
from django.core.urlresolvers import reverse

from ladder.models import Season
from ladder.views import season as season_view


class Command(BaseCommand):
    help = 'Refreshes cached pages'

    def handle(self, *args, **options):
        """
        Script that calls all season pages to refresh the cache on them if it has expired.

        Any time/date settings create postfixes on the caching key, for now the solution is to disable them.
        """

        if settings.USE_I18N:
            raise CommandError('USE_I18N in settings must be disabled.')

        if settings.USE_L10N:
            raise CommandError('USE_L10N in settings must be disabled.')

        if settings.USE_TZ:
            raise CommandError('USE_TZ in settings must be disabled.')

        self.factory = RequestFactory()
        seasons = Season.objects.all()
        for season in seasons:
            path = reverse('ladder:season', args=(unicode(season.end_date.year), unicode(season.season_round)))
            # use the request factory to generate the correct url for the cache hash
            request = self.factory.get(path)

            season_view(request, season.end_date.year, season.season_round)