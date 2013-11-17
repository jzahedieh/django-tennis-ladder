from django import forms
from ladder.models import Result, Player


class AddResultForm(forms.ModelForm):
    result = forms.IntegerField(min_value=0, max_value=8, label='Losing Result')

    # filter the player fields by ladder on init
    def __init__(self, ladder, *args, **kwargs):
        super(AddResultForm, self).__init__(*args, **kwargs)  # populates the post
        self.fields['opponent'].queryset = self.fields['player'].queryset = Player.objects.filter(league__ladder=ladder)

    class Meta:
        model = Result
        exclude = ['date_added', 'ladder']