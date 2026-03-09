from django.shortcuts import render

from .models import Lock
from .services.ttlock_api import TTLockAPI, TTLockAPIError


def home(request):
    """View that fetches lock list with TTLock API and returns the locks belonging to the logged user"""
    
    try:
        api = TTLockAPI()
        result = api.get_lock_list()

        # list is an array containing all the locks
        lock_list = result.get("list", [])

        # Fetch the user lock ids from the DB and insert them in a Set
        user_lock_ids = set(
            Lock.objects.filter(owner=request.user).values_list("ttlock_id", flat=True)
        )

        # Searching in a Set is instantaneous: complexity O(1)
        locks = [lock for lock in lock_list if lock["lockId"] in user_lock_ids]
        total = len(locks)

        return render(request, "home.html", {"locks": locks, "total": total})
    
    except TTLockAPIError as e:        
        context = {
            "locks": [],
            "total": 0,
            "api_error": "Non è stato possibile sincronizzare i dati con TTLock al momento. Riprova più tardi."
        }
        return render(request, "home.html", context)