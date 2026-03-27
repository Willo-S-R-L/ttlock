from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.cache import cache

from .models import Lock
from .forms import PasscodeForm

from .services.ttlock_api import TTLockAPI, TTLockAPIError


@login_required
def home(request):
    """
    View that fetches lock list with TTLock API and returns the locks
    belonging to the logged user
    """

    # Initialize cache to temporarily store the lock list, saving bandwidth
    # and decreasing latency every time the home page is loaded.
    # With cache_key each user has his own isolated cache
    cache_key = f"lock_list_user_{request.user.id}"
    lock_list = cache.get(cache_key)

    if lock_list is None:
        try:
            api = TTLockAPI()
            result = api.get_lock_list()

            # "list" field is an array containing all the locks
            lock_list = result.get("list", [])

        except TTLockAPIError:
            context = {
                "locks": [],
                "error": "Non è stato possibile recuperare i dati dei tuoi lock al momento. Riprova più tardi.",
            }
            return render(request, "home.html", context)

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

    context = {
        "locks": locks,
        "form": PasscodeForm(),
    }

    return render(request, "home.html", context)


@login_required
@require_POST
def lock_sync(request):
    """
    View that synchronizes data saved on local DB with the updated data on
    TTLock. When this view is called, the cache used in the home view is
    ignored.
    """

    try:
        api = TTLockAPI()
        result = api.get_lock_list()

    except TTLockAPIError:
        response = render(
            request,
            "home.html#error_feedback",
            {"error": "Sincronizzazione con TTLock fallita. Riprova più tardi."},
        )
        response["HX-Retarget"] = "#feedback"
        return response

    lock_list = result.get("list", [])

    # If the user is superuser return all the locks
    # else filter locks on TTLock based on the lock alias name
    # and save locally only the locks that are not present
    if request.user.is_superuser:
        locks = lock_list
    else:
        # Locks are associated with the user via naming convention: the prefix
        # before the first "_" corresponds to the user's username
        locks = [
            lock
            for lock in lock_list
            if lock["lockAlias"].split("_")[0].lower() == request.user.username.lower()
        ]

        for lock in locks:
            Lock.objects.get_or_create(ttlock_id=lock["lockId"], owner=request.user)

    # invalidate the cache so that the home page will reload the updated data
    cache.delete(f"lock_list_user_{request.user.id}")

    return render(
        request,
        "home.html#lock_grid",
        {
            "locks": locks,
            "form": PasscodeForm(),
        },
    )


@login_required
@require_POST
def passcode_add(request, lock_id):
    """
    View that validates passcode data and sends it to TTLock API to
    create the code. Finally, returns the result to the template.
    """

    # create a form instance and populate it with data from the request
    form = PasscodeForm(request.POST)
    # obtain lock id from the hidden field of the form

    if form.is_valid():
        # process the data in form.cleaned_data (a dictionary) as required
        code_name = form.cleaned_data["code_name"]
        is_custom = form.cleaned_data["is_custom"]
        custom_code = form.cleaned_data["custom_code"]
        duration = form.cleaned_data["duration"]
        start_date = form.cleaned_data["start_date"]
        end_date = form.cleaned_data["end_date"]

        data = {
            "lock_id": lock_id,
            "code_name": code_name,
            "is_custom": is_custom,
            "custom_code": custom_code,
            "duration": duration,
            "start_date": start_date,
            "end_date": end_date,
        }
    
        try:
            api = TTLockAPI()
            # API call to passcode endpoint
            api.create_passcode(data)

            response = render(
                request,
                "home.html#success_feedback",
                {"success": f"Passcode {code_name} creato con successo"},
            )
            response["HX-Trigger"] = "passcodeCreated"
            return response

        except TTLockAPIError:
            response = render(
                request,
                "home.html#error_feedback",
                {"error": "Creazione passcode fallita. Ritenta più tardi."},
            )
            response["HX-Retarget"] = f"#api-error-{lock_id}"
            return response

    # If validation errors of form fields occur return them in the form
    response = render(
        request, "home.html#passcode_form", {"form": form, "lock_id": lock_id}
    )
    response["HX-Retarget"] = f"#form-{lock_id}"
    response["HX-Reswap"] = "innerHTML"
    response["HX-Trigger"] = "passcodeError"
    return response
