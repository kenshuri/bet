from bet.models import Game, Bet, League
from accounts.models import CustomUser
import polars as pl

def compute_result(score1: int, score2: int):
    if score1 > score2:
        return "W"
    elif score1 < score2:
        return "L"
    else:
        return "D"


def game_result(league_id:int, game_id:int, user_id:int):
    """
    Pour calculer le résultat d'un match, il faut:
    - récupérer tous les bets existants sur un match dans la ligue donnée
    Parameters
    ----------
    league_id
    game_id
    user_id

    Returns
    -------

    """
    lg = League.objects.get(id=league_id)
    bets = Bet.objects.filter(league_id=league_id, game_id=game_id).values('id', 'game_id', 'league', 'user', 'score_team1', 'score_team2')
    game = Game.objects.filter(id=game_id).values('id', 'score_team1', 'score_team2')
    players_df = pl.from_records(list(lg.users.all().values('id', 'email', 'first_name'))).rename({
        'id': 'user_id'
    })
    game_df = pl.from_records(list(game)).rename(
        {'id': 'game_id',
         'score_team1': 'final_score_team1',
         'score_team2': 'final_score_team2'}
    )
    if bets.exists():
        bets_df = pl.from_records(list(bets)).rename({
            'id': 'bet_id',
            'league': 'league_id',
            'user': 'user_id',
            'score_team1': 'bet_score_team1',
            'score_team2': 'bet_score_team2',
        })
        df = bets_df.join(game_df, how='left', on=['game_id'], coalesce=True)
        if df.filter(pl.col('final_score_team1').is_not_null()).is_empty() == False and df.filter(pl.col('final_score_team2').is_not_null()).is_empty() == False:
            gm = Game.objects.get(id=game_id)

            df = (df.with_columns(
                pl.struct(['final_score_team1', 'final_score_team2'])
                .map_elements(lambda x: compute_result(x['final_score_team1'], x['final_score_team2']),
                              return_dtype=pl.String).alias('final_result'),
                pl.struct(['bet_score_team1', 'bet_score_team2'])
                .map_elements(lambda x: compute_result(x['bet_score_team1'], x['bet_score_team2']),
                              return_dtype=pl.String).alias('bet_result'))
            .with_columns(
                (pl.col('final_result') == pl.col('bet_result')).alias('bet_correct'))
            .with_columns(
                (pl.col('final_score_team1') == pl.col('bet_score_team1')).alias('bet_score1'),
                (pl.col('final_score_team2') == pl.col('bet_score_team2')).alias('bet_score2'))
            .with_columns(
                (pl.col('bet_score1') & pl.col('bet_score2')).alias('bet_perfect'))
            )

            correct_bets = df.filter(pl.col('bet_correct')).select(pl.len()).item()
            perfect_bets = df.filter(pl.col('bet_perfect')).select(pl.len()).item()

            if correct_bets != 0:
                correct_points = 1 / correct_bets * 100
            else:
                correct_points = 0.0
            if perfect_bets != 0:
                perfect_points = 1 / perfect_bets * lg.bonus_perfect
            else:
                perfect_points = 0.0

            if lg.bonus_stake == 1:
                if gm.game_type > 0:
                    stake_mult = 1 + 1/gm.game_type
                else:
                    stake_mult = 1
            else:
                stake_mult = 1

            df = df.with_columns(
                pl.lit(True).cast(pl.Boolean).alias('bet_exists'),
                (pl.col('bet_correct') * correct_points).alias('correct_points'),
                (pl.col('bet_perfect') * perfect_points).alias('perfect_points'),
            ).with_columns(
                (pl.col('correct_points') + pl.col('perfect_points')).alias('total_points_no_stake')
            ).with_columns(
                (pl.col('total_points_no_stake') * stake_mult).alias('total_points')
            )
        else:
            df = bets_df.with_columns(
                pl.lit(True).cast(pl.Boolean).alias('bet_exists'),
                pl.lit(None).cast(pl.Int64).alias('bet_correct'),
                pl.lit(None).cast(pl.Int64).alias('bet_perfect'),
                pl.lit(None).cast(pl.Int64).alias('total_points'),
                pl.lit(None).cast(pl.Int64).alias('perfect_points'),
                pl.lit(None).cast(pl.Int64).alias('correct_points'),
            )
    else:
        df = pl.DataFrame({
            'user_id': None,
            'bet_exists': None,
            'bet_correct': None,
            'bet_perfect': None,
            'total_points': None,
            'perfect_points': None,
            'correct_points': None,
            'bet_id': None,
            'bet_score_team1': None,
            'bet_score_team2': None,
        }).with_columns(
            pl.col('user_id').cast(pl.Int64),
            pl.col('bet_correct').cast(pl.Int64),
            pl.col('bet_perfect').cast(pl.Int64),
            pl.col('total_points').cast(pl.Int64),
            pl.col('perfect_points').cast(pl.Int64),
            pl.col('correct_points').cast(pl.Int64),
            pl.col('bet_id').cast(pl.Int64),
            pl.col('bet_score_team1').cast(pl.Int64),
            pl.col('bet_score_team2').cast(pl.Int64),
        )

    result_df = (players_df.join(df, how='left', on='user_id', coalesce=True)
               .with_columns(pl.col('total_points').fill_null(0),
                             pl.col('bet_exists').fill_null(False).cast(pl.Boolean))
               .sort(by=['total_points', 'bet_exists', 'first_name', 'bet_id'],
                     descending=[True, True, False, False]))

    user_score = result_df.filter(user_id=user_id).select('total_points').item()

    return result_df, user_score


class ResultDetail:
    user_id = int
    first_name = str
    bet_exists = bool
    bet_correct = bool
    bet_perfect = bool
    total_points = float
    bet_score_team1 = int
    bet_score_team2 = int

    def __init__(self, user_id:int, first_name:str, bet_exists:bool, bet_correct:bool, bet_perfect:bool, total_points:float, bet_score_team1:int, bet_score_team2:int) -> None:
        self.user_id = user_id
        self.first_name = first_name
        self.bet_exists = bet_exists
        self.bet_correct = bet_correct
        self.bet_perfect = bet_perfect
        self.total_points = total_points
        self.bet_score_team1 = bet_score_team1
        self.bet_score_team2 = bet_score_team2

class Result:
    league = League
    game = Game
    user = CustomUser
    result_df = pl.DataFrame
    result_list = list
    user_score = float

    def __init__(self, league_id: int, game_id: int, user_id:int):
        self.league = League.objects.get(id=league_id)
        self.game = Game.objects.get(id=game_id)
        self.user = CustomUser.objects.get(id=user_id)

        result_df, user_score = game_result(league_id, game_id, user_id)

        self.result_df = result_df
        self.user_score = user_score

        rl = list()
        for rd in result_df.iter_rows(named=True):
            rl.append(ResultDetail(
                user_id = rd['user_id'],
                first_name= rd['first_name'],
                bet_exists=rd['bet_exists'],
                bet_correct=rd['bet_correct'],
                bet_perfect=rd['bet_perfect'],
                total_points= rd['total_points'],
                bet_score_team1= rd['bet_score_team1'],
                bet_score_team2= rd['bet_score_team2'],
            ))

        self.result_list = rl


def get_results(game_id:int):
    game_qs = Game.objects.filter(pk=game_id).values('id', 'score_team1', 'score_team2')
    if not game_qs.exists():
        return pl.DataFrame()
    game = pl.from_records(list(game_qs)).rename(
            {'id': 'game_id',
             'score_team1': 'final_score_team1',
             'score_team2': 'final_score_team2'}
        )
    users = pl.from_records(list(CustomUser.objects.all().values('id', 'email', 'first_name'))).rename({
        'id': 'user_id'
    })

    bets_qs = Bet.objects.filter(game=game_id).values('id', 'game_id', 'league', 'user', 'score_team1', 'score_team2')
    if bets_qs.exists():
        bets = pl.from_records(list(bets_qs)).rename({
            'id': 'bet_id',
            'league': 'league_id',
            'user': 'user_id',
            'score_team1': 'bet_score_team1',
            'score_team2': 'bet_score_team2',
        })
        df = bets.join(game, how='left', on=['game_id'], coalesce=True)
        if df.filter(pl.col('final_score_team1').is_not_null()).is_empty() == False and df.filter(pl.col('final_score_team2').is_not_null()).is_empty() == False:
            df = (df.with_columns(
                pl.struct(['final_score_team1', 'final_score_team2'])
                .map_elements(lambda x: compute_result(x['final_score_team1'], x['final_score_team2']),
                              return_dtype=pl.String).alias('final_result'),
                pl.struct(['bet_score_team1', 'bet_score_team2'])
                .map_elements(lambda x: compute_result(x['bet_score_team1'], x['bet_score_team2']),
                              return_dtype=pl.String).alias('bet_result'))
            .with_columns(
                (pl.col('final_result') == pl.col('bet_result')).alias('bet_correct'))
            .with_columns(
                (pl.col('final_score_team1') == pl.col('bet_score_team1')).alias('bet_score1'),
                (pl.col('final_score_team2') == pl.col('bet_score_team2')).alias('bet_score2'))
            .with_columns(
                (pl.col('bet_score1') & pl.col('bet_score2')).alias('bet_perfect'))
            )

            correct_bets = df.filter(pl.col('bet_correct')).select(pl.len()).item()
            perfect_bets = df.filter(pl.col('bet_perfect')).select(pl.len()).item()

            if correct_bets != 0:
                correct_points = 1 / correct_bets * 100
            else:
                correct_points = 0.0
            if perfect_bets != 0:
                perfect_points = 1 / perfect_bets * 20
            else:
                perfect_points = 0.0

            df = df.with_columns(
                (pl.col('bet_correct') * correct_points).alias('correct_points'),
                (pl.col('bet_perfect') * perfect_points).alias('perfect_points'),
            ).with_columns((pl.col('correct_points') + pl.col('perfect_points')).alias('total_points'))
        else:
            df = bets.with_columns(
                pl.lit(None).cast(pl.Int64).alias('total_points'),
                pl.lit(None).cast(pl.Int64).alias('perfect_points'),
                pl.lit(None).cast(pl.Int64).alias('correct_points'),
            )
    else:
        bets = pl.DataFrame()
        df = pl.DataFrame({
            'user_id': None,
            'total_points': None,
            'perfect_points': None,
            'correct_points': None,
            'bet_id': None
        }).with_columns(
            pl.col('user_id').cast(pl.Int64),
            pl.col('total_points').cast(pl.Int64),
            pl.col('perfect_points').cast(pl.Int64),
            pl.col('correct_points').cast(pl.Int64),
            pl.col('bet_id').cast(pl.Int64)
        )

    results = (users.join(df, how='left', on='user_id')
             .fill_null(0)
             .sort(by=['total_points', 'perfect_points', 'correct_points', 'bet_id'], descending=True))

    return results

def get_table(league: int = 1):
    games_qs = Game.objects.filter(score_team1__isnull=False).filter(score_team2__isnull=False).values('id', 'score_team1', 'score_team2')
    users = pl.from_records(list(CustomUser.objects.all().values('id', 'email', 'first_name'))).rename({
        'id': 'user_id'
    })
    if games_qs.exists():
        # bets_qs = Bet.objects.filter(league=league).filter(game__in=games_qs.values('id')).values('id', 'game_id','league', 'user', 'score_team1', 'score_team2')
        bets_qs = Bet.objects.filter(game__in=games_qs.values('id')).values('id', 'game_id', 'league', 'user','score_team1', 'score_team2')
        games = pl.from_records(list(games_qs)).rename(
            {'id': 'game_id',
             'score_team1': 'final_score_team1',
             'score_team2': 'final_score_team2'}
        )
        bets = pl.from_records(list(bets_qs)).rename({
            'id':'bet_id',
            'league':'league_id',
            'user': 'user_id',
            'score_team1': 'bet_score_team1',
            'score_team2': 'bet_score_team2',
        })

        df = bets.join(games, how='left', on=['game_id'], coalesce=True)
        df = (df.with_columns(
            pl.struct(['final_score_team1', 'final_score_team2'])
            .map_elements(lambda x: compute_result(x['final_score_team1'], x['final_score_team2']), return_dtype=pl.String).alias('final_result'),
            pl.struct(['bet_score_team1', 'bet_score_team2'])
            .map_elements(lambda x: compute_result(x['bet_score_team1'], x['bet_score_team2']), return_dtype=pl.String).alias('bet_result'))
        .with_columns(
            (pl.col('final_result') == pl.col('bet_result')).alias('bet_correct'))
        .with_columns(
            (pl.col('final_score_team1') == pl.col('bet_score_team1')).alias('bet_score1'),
            (pl.col('final_score_team2') == pl.col('bet_score_team2')).alias('bet_score2'))
        .with_columns(
            (pl.col('bet_score1') & pl.col('bet_score2')).alias('bet_perfect'))
        )

        details = pl.DataFrame()
        for g in list(games.select('game_id').to_series()):
            aux = df.filter(pl.col('game_id')==g)

            total_bets = aux.select(pl.len()).item()
            correct_bets = aux.filter(pl.col('bet_correct')).select(pl.len()).item()
            perfect_bets = aux.filter(pl.col('bet_perfect')).select(pl.len()).item()

            if correct_bets != 0:
                correct_points = 1/correct_bets * 100
            else:
                correct_points = 0.0
            if perfect_bets != 0:
                perfect_points = 1/perfect_bets * 20
            else:
                perfect_points = 0.0

            aux = aux.with_columns(
                (pl.col('bet_correct') * correct_points).alias('correct_points'),
                (pl.col('bet_perfect') * perfect_points).alias('perfect_points'),
            ).with_columns((pl.col('correct_points') + pl.col('perfect_points')).alias('total_points'))

            details = details.vstack(aux)

        final_aux = details.group_by('user_id').agg(
            pl.col('bet_id').count(),
            pl.col('bet_correct').sum(),
            pl.col('bet_perfect').sum(),
            pl.col('correct_points').sum(),
            pl.col('perfect_points').sum(),
            pl.col('total_points').sum(),
        )

        final = (users.join(final_aux, how='left', on='user_id')
                 .fill_null(0)
                 .sort(by=['total_points', 'perfect_points', 'correct_points', 'bet_id'], descending=True))


    else:
        final = users.with_columns(
            pl.lit(0).alias('bet_id'),
            pl.lit(0).alias('bet_correct'),
            pl.lit(0).alias('bet_perfect'),
            pl.lit(0).alias('correct_points'),
            pl.lit(0).alias('perfect_points'),
            pl.lit(0).alias('total_points'),
        )

    return final