from ninja import Schema, Field
from ninja.orm import create_schema

from bet.models import Competition, Team, Game, Bet
from ninja import ModelSchema
import datetime

class TestIn(Schema):
    name: str

class TestOut(Schema):
    name:str

class TeamOut(Schema):
    name: str
    activity_type: int

class GameOut(Schema):
    id: int
    competition_id: int
    team_1_id: int
    team_2_id: int
    score_team1: int | None = None
    score_team2: int | None = None
    score_team1_after_ext: int | None = None
    score_team2_after_ext: int | None = None
    game_type: int
    start_datetime: datetime.datetime


class BetOut(Schema):
    id: int
    game_id: int
    user_id: int
    league_id: int
    score_team1: int
    score_team2: int

class BetIn(Schema):
    game_id: int
    user_id: int
    league_id: int
    score_team1: int
    score_team2: int

class BetsOut(Schema):
    existing_bets: list[BetOut]
    upcoming_bets: list[BetOut]
    past_bets: list[BetOut]


class PredictionOut(Schema):
    id_temp: int
    game_id: int
    start_datetime: datetime.datetime
    start_datetime_str: str
    started: bool
    todo: bool
    team_1__name: str
    team_2__name: str
    score_team1: int | None = None
    score_team2: int | None = None
    score_team1_after_ext: int | None = None
    score_team2_after_ext: int | None = None
    competition__name: str
    competition__short_name: str | None = None
    competition_id: int
    league__name: str
    league__short_name: str | None = None
    league_id: int
    bet_id: int | None = None
    bet_score_team1: int | None = None
    bet_score_team2: int | None = None

class UserScoreOut(Schema):
    user_id: int
    first_name: str
    bet_exists_count: int
    bet_ok_count: int
    bet_perfect_count: int
    total_points: float


class LeagueOut(Schema):
    league_id: int
    league__name: str
    league__short_name: str | None = None
    competition_id: int
    competition__name: str
    competition__short_name: str | None = None
    user_score: list[UserScoreOut]
