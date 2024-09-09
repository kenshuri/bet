import datetime
from typing import Optional

from django.utils import timezone

from ninja import Router, Schema
from silk.profiling.profiler import silk_profile
import polars as pl

from accounts.models import CustomUser
from bet.models import Team, Game, League, Bet, Competition
from api.schemas import TeamOut, GameOut, BetOut, BetsOut
from bet.utils import Result

router = Router()

@router.get("/teams/{int:user_id}", response=list[TeamOut])
def teams(request, user_id: int):
    data = Team.objects.filter(owner_id=user_id)
    return data


class Prediction:
    def __init__(self,
                 game_id: int,
                 start_datetime: datetime.datetime,
                 team_1__name: str,
                 team_2__name: str,
                 competition__name: str,
                 competition_id: int,
                 league__name: str,
                 league_id: int,
                 user_id: Optional[int] = None,
                 score_team1: Optional[int] = None,
                 score_team2: Optional[int] = None,
                 score_team1_after_ext: Optional[int] = None,
                 score_team2_after_ext: Optional[int] = None,
                 bet_id: Optional[int] = None,
                 bet_score_team1: Optional[int] = None,
                 bet_score_team2: Optional[int] = None):
        self.user_id = user_id
        self.game_id = game_id
        self.start_datetime = start_datetime
        self.team_1__name = team_1__name
        self.team_2__name = team_2__name
        self.score_team1 = score_team1
        self.score_team2 = score_team2
        self.score_team1_after_ext = score_team1_after_ext
        self.score_team2_after_ext = score_team2_after_ext
        self.competition__name = competition__name
        self.competition_id = competition_id
        self.league__name = league__name
        self.league_id = league_id
        self.bet_id = bet_id
        self.bet_score_team1 = bet_score_team1
        self.bet_score_team2 = bet_score_team2

class PredictionOut(Schema):
    user_id: int | None = None
    game_id: int
    start_datetime: datetime.datetime
    team_1__name: str
    team_2__name: str
    score_team1: int | None = None
    score_team2: int | None = None
    score_team1_after_ext: int | None = None
    score_team2_after_ext: int | None = None
    competition__name: str
    competition_id: int
    league__name: str
    league_id: int
    bet_id: int | None = None
    bet_score_team1: int | None = None
    bet_score_team2: int | None = None


@router.get("/predictions/{int:user_id}", response=list[PredictionOut])
def predictions(request, user_id: int):
    upcoming_games = (Game.objects.filter(competition__league__users=user_id)
                      .values('id', 'start_datetime',
                              'team_1__name', 'team_2__name',
                              'score_team1', 'score_team2',
                              'score_team1_after_ext', 'score_team2_after_ext',
                              'competition__name', 'competition_id',
                              'competition__league__name', 'competition__league__id'))
    ug = pl.from_records(list(upcoming_games)).rename({'id':'game_id',
                                                       'competition__league__name':'league__name',
                                                       'competition__league__id':'league_id'})
    upcoming_bets = (Bet.objects.filter(game__in=ug.get_column('game_id').unique().to_list())
                     .filter(user_id=user_id)
                     .values('id', 'game_id', 'user_id', 'league_id',
                             'score_team1', 'score_team2'))
    ub = pl.from_records(list(upcoming_bets)).rename({'id': 'bet_id', 'score_team1':'bet_score_team1', 'score_team2':'bet_score_team2'})
    data = ug.join(ub, how='left', on=['game_id', 'league_id']).sort('game_id', 'league_id')
    pred_list = list()
    for pred in data.iter_rows(named=True):
        pred_list.append(Prediction(user_id=pred['user_id'],
                                    game_id=pred['game_id'],
                                    start_datetime=pred['start_datetime'],
                                    team_1__name=pred['team_1__name'],
                                    team_2__name=pred['team_2__name'],
                                    score_team1=pred['score_team1'],
                                    score_team2=pred['score_team2'],
                                    score_team1_after_ext=pred['score_team1_after_ext'],
                                    score_team2_after_ext=pred['score_team2_after_ext'],
                                    competition__name=pred['competition__name'],
                                    competition_id=pred['competition_id'],
                                    league__name=pred['league__name'],
                                    league_id=pred['league_id'],
                                    bet_id=pred['bet_id'],
                                    bet_score_team1=pred['bet_score_team1'],
                                    bet_score_team2=pred['bet_score_team2']))
    return pred_list


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