from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import ModelForm
from django_email_blacklist import DisposableEmailChecker

from accounts.models import CustomUser
from bet.models import Bet, Game, League

class SignUpForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'password1', 'password2', )

    def __init__(self, *args, **kwargs):
        super(SignUpForm, self).__init__(*args, **kwargs)
        self.fields['password1'].help_text = 'Le mot doit faire plus de 8 caractères, ne pas être un mot de passe trop commun et ne pas être entièrement numérique.'

    def clean_email(self):
        email = self.cleaned_data['email']
        email_checker = DisposableEmailChecker()
        if email_checker.is_disposable(email):
            self.add_error('email', 'Utilisez une adresse email non-jetable svp')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error('password2', "Les deux mots de passe sont différents")
        return password2


class BetForm(forms.ModelForm):
    game = forms.ModelChoiceField(queryset=Game.objects.all(), widget=forms.HiddenInput())
    league = forms.ModelChoiceField(queryset=League.objects.all(), widget=forms.HiddenInput())

    class Meta:
        model = Bet
        fields = ['score_team1', 'score_team2', 'game', 'league']

