from django.apps import AppConfig


class LadderConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'ladder'

    def ready(self):
        import ladder.signals  # noqa: F401
