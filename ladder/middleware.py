from django.utils.cache import add_never_cache_headers


class DisableClientSideCachingMiddleware(object):
    """
    Disabled clients from doing local caching as it is handled by server
    See: http://stackoverflow.com/questions/2095520/fighting-client-side-caching-in-django
    """
    def process_response(self, request, response):
        add_never_cache_headers(response)
        return response