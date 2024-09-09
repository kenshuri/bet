from ninja import Schema, Field
from ninja.orm import create_schema

from bet.models import Competition, Team, Game, Bet
from ninja import ModelSchema
from datetime import datetime

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
    start_datetime: datetime


class BetOut(Schema):
    id: int
    game_id: int
    user_id: int
    league_id: int
    score_team1: int
    score_team2: int

class BetsOut(Schema):
    existing_bets: list[BetOut]
    upcoming_bets: list[BetOut]
    past_bets: list[BetOut]

