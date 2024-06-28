from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator


# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)

class Game(models.Model):
    euro_number = models.IntegerField(unique=True)
    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_1')
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_2')
    score_team1 = models.IntegerField(null=True, blank=True)
    score_team2 = models.IntegerField(null=True, blank=True)
    start_datetime = models.DateTimeField()


class League(models.Model):
    name = models.CharField(max_length=100)
    users = models.ManyToManyField(CustomUser, related_name='users')
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='owner')

class Bet(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    league = models.ForeignKey(League, on_delete=models.CASCADE)
    score_team1 = models.IntegerField(validators=[MinValueValidator(0)])
    score_team2 = models.IntegerField(validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('game', 'user', 'league')
