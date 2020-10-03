from django import forms
from ladder.models import Result, Player


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
    result = forms.IntegerField(min_value=0, max_value=8, label='Losing Result')
    winner = forms.BooleanField(label='Did you win?', required=False)

    # filter the player fields by ladder on init
    def __init__(self, ladder, user, *args, **kwargs):
        super(AddEntryForm, self).__init__(*args, **kwargs)
        self.fields['opponent'].queryset = Player.objects.filter(league__ladder=ladder).exclude(user=user)
        self.fields['player'].widget.attrs['value'] = Player.objects.get(user=user).id

    class Meta(object):
        model = Result
        exclude = ['date_added', 'ladder', 'inaccurate_flag']
        widgets = {'player': forms.HiddenInput()}

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