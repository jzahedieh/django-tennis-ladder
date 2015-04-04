from django import forms
from ladder.models import Result, Player


class AddResultForm(forms.ModelForm):
    result = forms.IntegerField(min_value=0, max_value=8, label=u'Losing Result')

    # filter the player fields by ladder on init
    def __init__(self, ladder, *args, **kwargs):
        super(AddResultForm, self).__init__(*args, **kwargs)  # populates the post
        self.fields[u'opponent'].queryset = self.fields[u'player'].queryset = Player.objects.filter(league__ladder=ladder)

    class Meta(object):
        model = Result
        exclude = [u'date_added', u'ladder']

    def clean(self):
        u"""
        Validation to make sure player does not equal opponent for result
        """

        # Make sure both keys are set
        try:
            player = self.cleaned_data[u'player']
            opponent = self.cleaned_data[u'opponent']
        except KeyError:
            # if not set return cleaned_data to allow for default validation to work
            return self.cleaned_data
        # Make the check
        if player == opponent:
            raise forms.ValidationError(u"Invalid Result: Player and Opponent cannot be the same person.", u'player_equals_opponent')
        else:
            return self.cleaned_data