from django.utils.cache import add_never_cache_headers

"""
Disabled clients from doing local caching as it is handled by server
See: http://stackoverflow.com/questions/2095520/fighting-client-side-caching-in-django
"""
class DisableClientCachingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        add_never_cache_headers(response)
        return response