from django import forms
from django.contrib.auth.models import User
from django.db.models import Q
from ladder.models import Result, Player


class EmailChangeForm(forms.Form):
    email = forms.EmailField(
        label='Email / Login',
        max_length=150,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        }),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        if 'initial' not in kwargs:
            kwargs['initial'] = {'email': user.email or user.username}
        super().__init__(*args, **kwargs)

    def clean_email(self):
        new_email = self.cleaned_data['email'].strip().lower()
        if User.objects.exclude(pk=self.user.pk).filter(
            Q(email__iexact=new_email) | Q(username__iexact=new_email)
        ).exists():
            raise forms.ValidationError("This email address is already in use by another account.")
        return new_email

    def save(self):
        new_email = self.cleaned_data['email']
        self.user.email = new_email
        self.user.username = new_email
        self.user.save(update_fields=['email', 'username'])
        return self.user


class AddResultForm(forms.ModelForm):
    result = forms.IntegerField(min_value=0, max_value=8, label='Losing Result')

    # filter the player fields by ladder on init
    def __init__(self, ladder, *args, **kwargs):
        super(AddResultForm, self).__init__(*args, **kwargs)  # populates the post
        self.fields['opponent'].queryset = self.fields['player'].queryset = Player.objects.filter(league__ladder=ladder)

    class Meta(object):
        model = Result
        exclude = ['date_added', 'ladder']

    def clean(self):
        """
        Validation to make sure player does not equal opponent for result
        """

        # Make sure both keys are set
        try:
            player = self.cleaned_data['player']
            opponent = self.cleaned_data['opponent']
        except KeyError:
            # if not set return cleaned_data to allow for default validation to work
            return self.cleaned_data
        # Make the check
        if player == opponent:
            raise forms.ValidationError("Invalid Result: Player and Opponent cannot be the same person.", 'player_equals_opponent')
        else:
            return self.cleaned_data

class AddEntryForm(forms.ModelForm):
    OUTCOME_CHOICES = [
        ('won', 'I Won'),
        ('lost', 'I Lost'),
        ('incomplete', 'Incomplete'),
    ]
    INCOMPLETE_REASON_CHOICES = [
        ('', '---------'),
        (Result.IncompleteReason.TIME, 'Ran out of time / conditions'),
        (Result.IncompleteReason.INJURY, 'Injury / retirement'),
    ]
    INJURED_PLAYER_CHOICES = [
        ('', '---------'),
        ('opponent', 'Opponent'),
        ('me', 'Me'),
    ]

    # add NumberInput with min/max so the template doesn't need to modify it
    result = forms.IntegerField(
        min_value=0, max_value=8, label='Losing Result',
        widget=forms.NumberInput(attrs={'min': 0, 'max': 8, 'class': 'form-control'})
    )
    opponent_result = forms.IntegerField(
        min_value=0, max_value=8, required=False, label="Opponent's Score",
        widget=forms.NumberInput(attrs={'min': 0, 'max': 8, 'class': 'form-control'})
    )
    winner = forms.BooleanField(
        label='Did you win?', required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    outcome = forms.ChoiceField(
        choices=OUTCOME_CHOICES, required=False,
        widget=forms.HiddenInput()
    )
    incomplete_reason = forms.ChoiceField(
        choices=INCOMPLETE_REASON_CHOICES, required=False,
        widget=forms.HiddenInput()
    )
    injured_player = forms.ChoiceField(
        choices=INJURED_PLAYER_CHOICES, required=False,
        widget=forms.HiddenInput()
    )

    def __init__(self, ladder, user, *args, **kwargs):
        super(AddEntryForm, self).__init__(*args, **kwargs)
        self.fields['opponent'].queryset = Player.objects.filter(league__ladder=ladder).exclude(user=user)
        self.fields['opponent'].label_from_instance = self.opponent_label
        self.fields['opponent'].widget.attrs.update({'class': 'form-select'})
        self.fields['player'].widget.attrs['value'] = Player.objects.get(user=user).id
        # ensure hidden has bootstrap class if you care; not required
        self.fields['player'].widget.attrs.update({'class': 'd-none'})

    class Meta(object):
        model = Result
        exclude = ['date_added', 'ladder', 'entered_by']
        widgets = {'player': forms.HiddenInput()}

    @staticmethod
    def opponent_label(player):
        return player.first_name + " " + player.last_name

    def clean(self):
        cleaned_data = super(AddEntryForm, self).clean()
        try:
            player = cleaned_data['player']
            opponent = cleaned_data['opponent']
        except KeyError:
            return cleaned_data
        if player == opponent:
            raise forms.ValidationError("Invalid Result: Player and Opponent cannot be the same person.", 'player_equals_opponent')

        outcome = cleaned_data.get('outcome')
        if not outcome:
            outcome = 'won' if cleaned_data.get('winner') else 'lost'
        cleaned_data['outcome'] = outcome

        if outcome == 'incomplete':
            reason = cleaned_data.get('incomplete_reason')
            if reason not in (Result.IncompleteReason.TIME, Result.IncompleteReason.INJURY):
                raise forms.ValidationError(
                    "Please select a reason for the incomplete match.",
                    'missing_incomplete_reason',
                )
            if reason == Result.IncompleteReason.TIME:
                if cleaned_data.get('opponent_result') is None:
                    raise forms.ValidationError(
                        "Please select your opponent's score for an incomplete match.",
                        'missing_opponent_result',
                    )
            elif reason == Result.IncompleteReason.INJURY:
                injured = cleaned_data.get('injured_player')
                if injured not in ('opponent', 'me'):
                    raise forms.ValidationError(
                        "Please select who retired due to injury.",
                        'missing_injured_player',
                    )
        else:
            cleaned_data['incomplete_reason'] = None

        return cleaned_data