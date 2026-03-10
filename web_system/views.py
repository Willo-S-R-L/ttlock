from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.cache import cache

from .models import Lock

from .services.ttlock_api import TTLockAPI, TTLockAPIError


@login_required
@require_http_methods("GET, POST")
def home(request):
    """View that fetches lock list with TTLock API and returns the locks belonging to the logged user"""

    try:
        # Initialize cache to temporarily store the lock list, saving bandwidth
        # and decreasing latency every time the home page is loaded.
        # With cache_key each user has his own isolated cache
        cache_key = f"lock_list_user_{request.user.id}"
        lock_list = cache.get(cache_key)

        if lock_list is None:
            api = TTLockAPI()
            result = api.get_lock_list()

            # "list" field is an array containing all the locks
            lock_list = result.get("list", [])

            # Cache lock_list for 60 seconds
            cache.set(cache_key, lock_list, timeout=60)

        # Fetch the user lock ids from the DB and insert them in a Set
        user_lock_ids = set(
            Lock.objects.filter(owner=request.user).values_list("ttlock_id", flat=True)
        )

        # If the user is superuser show all the locks
        if request.user.is_superuser:
            locks = lock_list
        else:
            # Search the locks belonging to the user
            # Searching in a Set is instantaneous: complexity O(1)
            locks = [lock for lock in lock_list if lock["lockId"] in user_lock_ids]

        total = len(locks)

        return render(request, "home.html", {"locks": locks, "total": total})

    except TTLockAPIError as e:
        context = {
            "locks": [],
            "total": 0,
            "api_error": "Non è stato possibile recuperare i dati dei tuoi lock al momento. Riprova più tardi.",
        }
        return render(request, "home.html", context)

