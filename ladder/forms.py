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
    # add NumberInput with min/max so the template doesn't need to modify it
    result = forms.IntegerField(
        min_value=0, max_value=8, label='Losing Result',
        widget=forms.NumberInput(attrs={'min': 0, 'max': 8, 'class': 'form-control'})
    )
    winner = forms.BooleanField(label='Did you win?', required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

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
        exclude = ['date_added', 'ladder', 'inaccurate_flag']
        widgets = {'player': forms.HiddenInput()}

    @staticmethod
    def opponent_label(player):
        return player.first_name + " " + player.last_name

    def clean(self):
        try:
            player = self.cleaned_data['player']
            opponent = self.cleaned_data['opponent']
        except KeyError:
            return self.cleaned_data
        if player == opponent:
            raise forms.ValidationError("Invalid Result: Player and Opponent cannot be the same person.", 'player_equals_opponent')
        return self.cleaned_data