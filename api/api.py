import datetime
from typing import Optional

from django.utils import timezone

from ninja import Router, Schema, Form
from silk.profiling.profiler import silk_profile
import polars as pl

from accounts.models import CustomUser
from bet.models import Team, Game, League, Bet, Competition
from api.schemas import TeamOut, GameOut, BetOut, BetsOut, PredictionOut, TestIn, TestOut, BetIn
from bet.utils import get_predictions

router = Router()

@router.get("/teams/{int:user_id}", response=list[TeamOut])
def teams(request, user_id: int):
    data = Team.objects.filter(owner_id=user_id)
    return data


@router.get("/predictions/{int:user_id}", response=list[PredictionOut])
def predictions(request, user_id: int):
    # TODO: Check authentication/authorization
    data = get_predictions(user_id)
    return data.to_dicts()

@router.post("/test", response=BetOut)
def test(request, bet: Form[BetIn]):
    return bet


@router.get("/games", response=list[GameOut])
def games(request):
    games = Game.objects.all()
    bets = Bet.objects.all()
    return games

@router.get("/results/{int:user_id}", response=list[GameOut])
def results(request, user_id: int):
    #data = Game.objects.filter(competition__in=CustomUser.objects.get(id=user_id).leagues_played.all().values('competition').distinct())
    leagues = League.objects.filter(users=user_id)
    data = pl.DataFrame()
    for l in leagues:
        print(pl.from_records(list(l.competition.game_set.all().values('id', 'competition'))).with_columns(pl.lit(4).alias('league')))
        l.users.all()


    games = Game.objects.filter(competition__in=League.objects.filter(users=user_id).values('competition').distinct()).filter(start_datetime__lt=timezone.now())
    games_df = pl.from_records(list(games.values('id', 'competition', 'start_datetime'))).rename({'id':'game'})
    bets = Bet.objects.filter(game__in=games)
    bets_df = pl.from_records(list(bets.values('id', 'user','game', 'league'))).rename({'id':'bet'})
    data = games_df.join(bets_df, how='left', on='game').sort(['competition', 'game', 'league', 'bet'])
    return data