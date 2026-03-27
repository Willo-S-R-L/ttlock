from django import forms
from django.utils import timezone

from datetime import timedelta


# x-model is used by Alpine.js to associate a field to a variable name
# then this name is used to set default value to the field and to reset
# its value after submission
class PasscodeForm(forms.Form):
    code_name = forms.CharField(
        required=True,
        max_length=50,
        error_messages={
            "required": "Il nome è obbligatorio",
            "max_length": "Il nome può contenere al massimo 50 caratteri",
        },
        widget=forms.TextInput(
            attrs={
                "class": "input w-full",
                "placeholder": "Inserisci nome passcode",
                "x-model": "lockName",
            }
        ),
    )

    is_custom = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "class": "toggle toggle-primary rounded-full\
                    [&::before]:rounded-full text-primary checked:text-primary",
                "x-model": "isCustom",
            }
        ),
    )

    custom_code = forms.CharField(
        min_length=4,
        max_length=9,
        required=False,
        error_messages={
            "min_length": "Il codice deve contenere almeno 4 cifre",
            "max_length": "Il codice può contenere al massimo 9 cifre",
        },
        widget=forms.TextInput(
            attrs={
                "class": "input w-full",
                # min 4 digits, max 9 digits:
                "pattern": "[0-9]{4,9}",
                # show numeric pad on mobile:
                "inputmode": "numeric",
                "placeholder": "Inserisci codice numerico",
                ":disabled": "!isCustom",
                ":required": "isCustom",
                "x-model": "customCode",
                # allows the entry of only numers in the field:
                "@input": "$el.value = $el.value.replace(/[^0-9]/g, '')",
            }
        ),
    )

    duration = forms.ChoiceField(
        required=True,
        error_messages={
            "required": "La durata è obbligatoria",
        },
        choices=[
            ("permanente", "Permanente"),
            ("monouso", "Monouso"),
            ("temporanea", "Temporanea"),
        ],
    )

    start_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "input",
                "x-model": "startDate",
                # set the min value of start date to the current day:
                ":min": "now",
                ":max": "endDate || ''",
                ":disabled": "duration !== 'temporanea'",
                ":required": "duration === 'temporanea'",
                # removes minutes from the user-selected time:
                "@change": "$el.value = $el.value.slice(0,13) + ':00'",
            }
        ),
    )

    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "input",
                "x-model": "endDate",
                # set min value to startDate, else to current date:
                ":min": "startDate || now",
                # set max value to no more than one year:
                ":max": "getMaxEndDate(startDate)",
                ":disabled": "duration !== 'temporanea'",
                ":required": "duration === 'temporanea'",
                # removes minutes from the user-selected time:
                "@change": "$el.value = $el.value.slice(0,13) + ':00'",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        is_custom = cleaned_data.get("is_custom")
        duration = cleaned_data.get("duration")

        if is_custom:
            custom_code = cleaned_data.get("custom_code")
            
            if custom_code and not custom_code.isdigit():
                self.add_error("custom_code", "Il codice può contenere solo numeri")

        if duration not in ("permanente", "monouso", "temporanea"):
            self.add_error("duration", "Durata non valida")

        if duration == "temporanea":
            start_date = cleaned_data.get("start_date")
            end_date = cleaned_data.get("end_date")

            if not start_date:
                self.add_error("start_date", "La data di inizio è obbligatoria")
            if not end_date:
                self.add_error("end_date", "La data di fine è obbligatoria")

            if start_date and end_date:
                start_date = start_date.replace(minute=0, second=0, microsecond=0)
                cleaned_data["start_date"] = start_date

                end_date = end_date.replace(minute=0, second=0, microsecond=0)
                cleaned_data["end_date"] = end_date

                if start_date > end_date:
                    self.add_error(
                        "start_date",
                        "La data di inizio deve essere precedente alla data di fine",
                    )
                if start_date < timezone.now().replace(
                    minute=0, second=0, microsecond=0
                ):
                    self.add_error(
                        "start_date", "La data di inizio non può essere nel passato"
                    )

                limit = start_date + timedelta(days=365)
                if end_date > limit:
                    self.add_error(
                        "end_date", "La durata massima consentita è di un anno"
                    )

        return cleaned_data
