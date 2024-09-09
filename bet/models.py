import uuid

from django.db import models
from accounts.models import CustomUser
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class OwnerType(models.IntegerChoices):
    OFFICIAL = 1, _('Official')
    CUSTOM = 2, _('Custom')


class ActivityType(models.IntegerChoices):
    MIXED = 0, _('Mixed')  #  For a competition -> means that any type of team can participate, for a team -> means it's a country team
    FOOTBALL = 1001, _('Football')
    TENNIS = 1002, _('Tennis')


class GameType(models.IntegerChoices):
    STANDARD = 0, _('Standard')
    FINAL_1_1 = 1, _('Final')
    FINAL_1_2 = 2, _('Semi-Final')
    FINAL_1_4 = 4, _('Quarter-Final')
    FINAL_1_8 = 8, _('Round of 16')
    FINAL_1_16 = 16, _('Round of 32')
    FINAL_1_32 = 32, _('Round of 64')
    FINAL_1_64 = 64, _('Round of 128')


# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=1)
    # TODO: set back to owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=0)
    activity_type = models.IntegerField(choices=ActivityType.choices, default=ActivityType.MIXED)

    def __str__(self):
        return f"{self.name}"

    def is_official(self):
        return self.owner.is_staff


class Competition(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=5, null=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=0, related_name='cp_owner')
    activity_type = models.IntegerField(choices=ActivityType.choices)

    def __str__(self):
        return f"{self.name}"

    def is_official(self):
        return self.owner.is_staff

    def sn(self):
        if self.short_name:
            return self.short_name
        else:
            return self.name[0:5]


class Game(models.Model):
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, null=True, blank=True)
    #TODO: To change back to on_delete=models.SET_DEFAULT, default=0 and remove null=TRUE & blank=TRUE
    competition_number = models.IntegerField(unique=False, blank=True, null=True)
    team_1 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_1')
    team_2 = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_2')
    score_team1 = models.IntegerField(null=True, blank=True)
    score_team2 = models.IntegerField(null=True, blank=True)
    score_team1_after_ext = models.IntegerField(null=True, blank=True)
    score_team2_after_ext = models.IntegerField(null=True, blank=True)
    game_type = models.IntegerField(choices=GameType.choices, default=GameType.STANDARD)
    start_datetime = models.DateTimeField()

    def __str__(self):
        return f"{self.id}-{self.competition.sn()}: {self.team_1} vs {self.team_2}"


class StakeChoice(models.IntegerChoices):
    STAKE_0 = 0, _('No bonus')
    STAKE_1 = 1, _('Bonus Mode 1')


class PerfectChoice(models.IntegerChoices):
    PERFECT_0 = 0, _('No perfect bonus')
    PERFECT_10 = 10, _('Perfect bonus 10')
    PERFECT_20 = 20, _('Perfect bonus 20')
    PERFECT_50 = 50, _('Perfect bonus 50')
    PERFECT_100 = 100, _('Perfect bonus 100')


class League(models.Model):
    name = models.CharField(max_length=100)
    short_name = models.CharField(max_length=5, null=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=0, related_name='leagues_owned')
    users = models.ManyToManyField(CustomUser, related_name='leagues_played')
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, null=True, blank=True)
    #TODO: TO change back to competition = models.ForeignKey(Competition, on_delete=models.SET_DEFAULT, default=0, related_name='lg_competition')
    bonus_stake = models.IntegerField(choices=StakeChoice.choices, default=StakeChoice.STAKE_0)
    bonus_perfect = models.IntegerField(choices=PerfectChoice.choices, default=PerfectChoice.PERFECT_20)
    with_ext = models.BooleanField(default=False)
    code = models.CharField(max_length=36, default=uuid.uuid4)



    def __str__(self):
        return f"{self.name}"


    def sn(self):
        if self.short_name:
            return self.short_name
        else:
            return self.name[0:5]


class Bet(models.Model):
    game = models.ForeignKey(Game, on_delete=models.SET_DEFAULT, default=0)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_DEFAULT, default=0)
    league = models.ForeignKey(League, on_delete=models.SET_DEFAULT, default=0)
    score_team1 = models.IntegerField(validators=[MinValueValidator(0)])
    score_team2 = models.IntegerField(validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ('game', 'user', 'league')

    def __str__(self):
        return f"{self.user} bet on {self.game} in league {self.league}"