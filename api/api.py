import datetime
from typing import Optional

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.utils import IntegrityError
from django_browser_reload.views import message

from ninja import Router, Schema, Form, NinjaAPI
# from silk.profiling.profiler import silk_profile
import polars as pl
from polars import Boolean
from pydantic import field_validator

from accounts.models import CustomUser
from bet.forms import BetForm
from bet.models import Team, Game, League, Bet, Competition
from api.schemas import TeamOut, GameOut, BetOut, BetsOut, PredictionOut, TestIn, TestOut, BetIn, LeagueOut
from bet.utils import get_predictions, get_leagues, LeagueScore

router = Router()
api = NinjaAPI()

@router.get("/teams/{int:user_id}", response=list[TeamOut])
def teams(request, user_id: int):
    data = Team.objects.filter(owner_id=user_id)
    return data


@router.get("/predictions/{int:user_id}", response=list[PredictionOut])
def predictions(request, user_id: int):
    # TODO: Check authentication/authorization
    data = get_predictions(user_id)
    return data.to_dicts()

@router.get("/leagues/{int:user_id}", response=list[LeagueOut])
def leagues(request, user_id: int):
    # TODO: Check authentication/authorization
    data = get_leagues(user_id)
    x = [LeagueScore(data[i]) for i in range(len(data))]
    return x


@router.post("/bet", response=BetOut)
def create_bet(request, bet: BetIn):
    bet_dict = bet.model_dump()
    created_bet = Bet(**bet_dict)

    ## Validate data based on Bet models
    try:
        created_bet.full_clean()
    except ValidationError as e:
        message = str(e)
        return api.create_response(
            request,
            {"message": message},
            status=400,
        )

    created_bet = Bet.objects.create(**bet_dict)
    return created_bet



@router.put("/bet/{bet_id}", response=BetOut)
def update_bet(request, bet_id: int, bet: BetIn):
    updated_bet = get_object_or_404(Bet, id=bet_id)
    for attr, value in bet.dict().items():
        setattr(updated_bet, attr, value)

    ## Validate data based on Bet models
    try:
        updated_bet.full_clean()
    except ValidationError as e:
        message = str(e)
        return api.create_response(
            request,
            {"message": message},
            status=400,
        )

    updated_bet.save()
    return updated_bet



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