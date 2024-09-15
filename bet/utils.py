from django.utils import timezone

from bet.models import Game, Bet, League
from accounts.models import CustomUser
import polars as pl


def get_predictions(user_id:int) -> list[pl.DataFrame]:
    upcoming_games = (Game.objects.filter(competition__league__users=user_id)
                      .values('id', 'start_datetime',
                              'team_1__name', 'team_2__name',
                              'score_team1', 'score_team2',
                              'score_team1_after_ext', 'score_team2_after_ext',
                              'competition__name', 'competition_id', 'competition__short_name',
                              'competition__league__name', 'competition__league__id', 'competition__league__short_name'))
    ug = pl.from_records(list(upcoming_games)).rename({'id': 'game_id',
                                                       'competition__league__name': 'league__name',
                                                       'competition__league__id': 'league_id',
                                                       'competition__league__short_name': 'league__short_name'})
    upcoming_bets = (Bet.objects.filter(game__in=ug.get_column('game_id').unique().to_list())
                     .filter(user_id=user_id)
                     .values('id', 'game_id', 'league_id',
                             'score_team1', 'score_team2'))
    ub = pl.from_records(list(upcoming_bets)).rename(
        {'id': 'bet_id', 'score_team1': 'bet_score_team1', 'score_team2': 'bet_score_team2'})
    data = ug.join(ub, how='left', on=['game_id', 'league_id']).sort('game_id', 'league_id')
    data = data.with_columns(
        pl.when(pl.col('start_datetime') < timezone.now()).then(True).otherwise(False).alias('started'),
        pl.col('start_datetime').dt.convert_time_zone("Europe/Paris").dt.strftime("%d/%m/%Y %H:%M").alias("start_datetime_str")
    ).with_row_index('id_temp', offset=1
    ).with_columns(pl.when((pl.col('started') == False) & (pl.col('bet_id').is_null())).then(True).otherwise(False).alias('todo'),
    ).sort('start_datetime','competition_id','league_id', 'game_id')
    return data




class LeagueScore:
    league_id: int
    league__name: str
    league__short_name: str | None = None
    competition_id: int
    competition_name: str
    competition_short_name: str | None = None
    user_score: dict

    def __init__(self, df):
        self.league_id = df['league_id'].item(0)
        self.league__name = df['league__name'].item(0)
        self.league__short_name = df['league__short_name'].item(0)
        self.competition_id = df['competition_id'].item(0)
        self.competition__name = df['competition__name'].item(0)
        self.competition__short_name = df['competition__short_name'].item(0)
        self.user_score = df.to_dicts()


def get_leagues(user_id:int) -> pl.DataFrame:
    user_games = Game.objects.filter(competition__league__users=user_id).filter(
        score_team1__isnull=False, score_team2__isnull=False
    ).values(
        'id', 'start_datetime', 'game_type',
        'team_1__name', 'team_2__name',
        'score_team1', 'score_team2',
        'score_team1_after_ext', 'score_team2_after_ext',
        'competition__name', 'competition_id', 'competition__short_name',
        'competition__league__name', 'competition__league__id', 'competition__league__short_name'
    )
    ug = pl.from_records(list(user_games)).rename({'id': 'game_id',
                                                       'competition__league__name': 'league__name',
                                                       'competition__league__id': 'league_id',
                                                       'competition__league__short_name': 'league__short_name'})
    league_users = CustomUser.objects.filter(
        leagues_played__in=ug.get_column('league_id').unique().to_list()
    ).values('id', 'first_name', 'leagues_played', 'leagues_played__bonus_perfect',
             'leagues_played__bonus_stake', 'leagues_played__with_ext')
    lu = pl.from_records(list(league_users)).rename({'id': 'user_id'})

    data = ug.join(lu, how='left', left_on='league_id', right_on='leagues_played')

    users_bets = Bet.objects.filter(
        user_id__in=data.get_column('user_id').unique().to_list()
    ).filter(
        league_id__in=data.get_column('league_id').unique().to_list()
    ).values('id', 'league_id', 'user_id', 'game_id', 'score_team1', 'score_team2')
    ub = pl.from_records(list(users_bets)).rename({
        'id':'bet_id',
        'score_team1': 'bet_score_team1',
        'score_team2': 'bet_score_team2',
    })

    data = data.join(ub, how='left', on=['user_id', 'league_id', 'game_id'])

    data = data.rename({
        'score_team1': 'score_team1_before_ext',
        'score_team2': 'score_team2_before_ext',
    }).with_columns(
        pl.when((pl.col('leagues_played__with_ext') == True) &
                (pl.col('score_team1_after_ext').is_not_null()) &
                (pl.col('score_team2_after_ext').is_not_null()))
        .then(True)
        .otherwise(False).alias('result_after_ext')
    ).with_columns(
        pl.when(pl.col('result_after_ext') == True)
        .then('score_team1_after_ext')
        .otherwise('score_team1_before_ext')
        .alias('score_team1'),
        pl.when(pl.col('result_after_ext') == True)
        .then('score_team2_after_ext')
        .otherwise('score_team2_before_ext')
        .alias('score_team2')
    ).with_columns(
        pl.when(pl.col('score_team1')>pl.col('score_team2')).then(1)
        .when(pl.col('score_team1')<pl.col('score_team2')).then(2)
        .when(pl.col('score_team1')==pl.col('score_team2')).then(3)
        .otherwise(0).alias('game_result'),
        pl.when(pl.col('bet_score_team1')>pl.col('bet_score_team2')).then(1)
        .when(pl.col('bet_score_team1')<pl.col('bet_score_team2')).then(2)
        .when(pl.col('bet_score_team1')==pl.col('bet_score_team2')).then(3)
        .otherwise(0).alias('bet_result')
    ).with_columns(
        pl.when(pl.col('bet_result') != 0)
        .then(True).otherwise(False).alias('bet_exists'),
        pl.when(pl.col('bet_result') == pl.col('game_result'))
        .then(True).otherwise(False).alias('bet_ok'),
        pl.when((pl.col('score_team1') == pl.col('bet_score_team1'))
                & (pl.col('score_team2') == pl.col('bet_score_team2')))
        .then(True).otherwise(False).alias('bet_perfect')
    )

    bet_calc = data.group_by(['game_id', 'league_id']).agg(
        [pl.col('bet_ok').sum().alias('bet_ok_count'),
         pl.col('bet_perfect').sum().alias('bet_perfect_count'),
         ]
    )

    data = data.join(bet_calc, on=['game_id', 'league_id'], how='left').with_columns(
        pl.when(pl.col('bet_ok') == True)
        .then(100 / pl.col('bet_ok_count'))
        .otherwise(0).alias('ok_points'),
        pl.when(pl.col('bet_perfect') == True)
        .then(pl.col('leagues_played__bonus_perfect') / pl.col('bet_perfect_count'))
        .otherwise(0).alias('perfect_points'),
    ).with_columns(
        pl.when((pl.col('leagues_played__bonus_stake') == 1) & (pl.col('game_type') != 0))
        .then(1 + 1/pl.col('game_type')).otherwise(1).alias('stake_factor'),
    ).with_columns(
        ((pl.col('ok_points') + pl.col('perfect_points')) * pl.col('stake_factor')).round(4).alias('total_points'),
    )

    leagues = data.group_by(['league_id', 'league__name', 'league__short_name',
                   'competition_id', 'competition__name', 'competition__short_name',
                   'user_id', 'first_name']).agg(
        [
            pl.col('bet_exists').sum().alias('bet_exists_count'),
            pl.col('bet_ok').sum().alias('bet_ok_count'),
            pl.col('bet_perfect').sum().alias('bet_perfect_count'),
            pl.col('total_points').sum().alias('total_points'),
        ]
    ).sort('league_id', 'total_points', 'first_name',
           descending=[False, True, False])
    leagues_list = [leagues.filter(pl.col('league_id') == id) for id in leagues.get_column('league_id').unique().to_list()]
    return leagues_list


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
                               pl.col('bet_correct').fill_null(False).cast(pl.Boolean),
                               pl.col('bet_perfect').fill_null(False).cast(pl.Boolean),
                               pl.col('bet_exists').fill_null(False).cast(pl.Boolean))
                 .sort(by=['total_points', 'bet_exists', 'first_name', 'bet_id'],
                       descending=[True, True, False, False]))

    user_score = result_df.filter(user_id=user_id).select('total_points').item()

    return result_df, user_score



def league_ranking(league_id:int, user_id:int):
    """
    POur calculer le ranking d'une league, il faut:
        Récupérer tous les jouers inscrits sur cette league
        Récupérer tous les matchs définis sur la compétition de cette league pour lesquels les score définitifs sont disponibles
            Pour chaque match -->
            Récupérer tous les bets des joueurs inscrits
            Calculer les points de l'ensemble des joueurs pour un match
            Stocker les derniers résultats du user
        Faire la somme des points pour chaque match
        Récupérer les points totals du user

    Parameters
    ----------
    league_id
    user_id

    Returns
    -------

    """
    users = CustomUser.objects.filter(leagues_played__in=[league_id]).distinct()
    competition = League.objects.filter(id=league_id).values('competition')
    games = Game.objects.filter(competition__in=competition).filter(score_team1__isnull=False).filter(score_team2__isnull=False).values('id').order_by('start_datetime')

    games_results_list = list()
    last_results_list = list()
    ranking = pl.DataFrame({
        'user_id': [u.id for u in users],
        'first_name': [u.first_name for u in users],
        'email': [u.email for u in users],
    })
    ranking = ranking.with_columns(
        pl.lit(0).alias('bets_number'),
        pl.lit(0).alias('bets_ok'),
        pl.lit(0).alias('bets_perfect'),
        pl.lit(0).alias('user_score').cast(pl.Float64),
    )
    for g in games:
        g_result_df, u_score = game_result(league_id=league_id, game_id=g['id'], user_id=user_id)
        # g_result_df = g_result_df.with
        ranking = ranking.join(g_result_df.select('user_id', 'bet_exists', 'bet_correct', 'bet_perfect', 'total_points'),
                               how='left', on='user_id', coalesce=True).with_columns(
            (pl.col('bets_number') + pl.col('bet_exists').cast(pl.Int64)).alias('bets_number'),
            (pl.col('bets_ok') + pl.col('bet_correct').cast(pl.Int64)).alias('bets_ok'),
            (pl.col('bets_perfect') + pl.col('bet_perfect').cast(pl.Int64)).alias('bets_perfect'),
            (pl.col('user_score') + pl.col('total_points').cast(pl.Int64)).alias('user_score'),
        ).select(
            'first_name', 'user_id', 'email', 'bets_number', 'bets_ok', 'bets_perfect', 'user_score'
        )
        games_results_list.append(g_result_df)
        l_result = 0
        if g_result_df.filter(pl.col('user_id') == user_id).select('bet_perfect').item() == True:
            l_result = 3 # Perfect
        elif g_result_df.filter(pl.col('user_id') == user_id).select('bet_correct').item() == True:
            l_result = 2 # Correct
        elif g_result_df.filter(pl.col('user_id') == user_id).select('bet_exists').item() == True:
            l_result = 1  # Wrong
        else:
            l_result = 0  # No bet
        last_results_list.append(l_result)
    ranking = ranking.sort('user_score', 'bets_ok', descending=True)
    ranking = ranking.with_columns(
        pl.col('user_score').rank(method='min', descending=True).alias('user_rank'),
    )

    if len(last_results_list) < 5:
        last_results_list = [*[-1 for x in range(5-len(last_results_list))], *last_results_list]

    user_rank = ranking.filter(pl.col('user_id')==user_id).select('user_rank').item()
    user_score = ranking.filter(pl.col('user_id')==user_id).select('user_score').item()

    return ranking, last_results_list[-4:], user_score, user_rank


class RankingDetail:
    user_id: int
    first_name: str
    bets_number: int
    bets_ok: int
    bets_perfect: int
    user_score: float

    def __init__(self, user_id: int, user_rank: int, first_name: str, bets_number: int, bets_ok: int, bets_perfect: int, user_score: float):
        self.user_id = user_id
        self.user_rank = user_rank
        self.first_name = first_name
        self.bets_number = bets_number
        self.bets_ok = bets_ok
        self.bets_perfect = bets_perfect
        self.user_score = user_score

class Ranking:
    user: CustomUser
    league: League
    last_results: list[int]
    ranking_df: pl.DataFrame
    user_score: float
    ranking_list: list[RankingDetail]
    user_rank = int

    def __init__(self, user_id: int, league_id: int):
        self.user = CustomUser.objects.get(id=user_id)
        self.league = League.objects.get(id=league_id)

        ranking_df, last_results, user_score, user_rank = league_ranking(league_id, user_id)

        self.ranking_df = ranking_df
        self.last_results = last_results
        self.user_score = user_score
        self.user_rank = user_rank

        rl = list()
        for rd in ranking_df.iter_rows(named=True):
            rl.append(RankingDetail(
                user_id=rd['user_id'],
                user_rank=rd['user_rank'],
                first_name=rd['first_name'],
                bets_number=rd['bets_number'],
                bets_ok=rd['bets_ok'],
                bets_perfect=rd['bets_perfect'],
                user_score=rd['user_score']
            ))

        self.ranking_list = rl




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
    league: League
    game: Game
    user: CustomUser
    result_df: pl.DataFrame
    result_list: list
    user_score: float
    user_bet: int

    def __init__(self, league_id: int, game_id: int, user_id:int):
        self.league = League.objects.get(id=league_id)
        self.game = Game.objects.get(id=game_id)
        self.user = CustomUser.objects.get(id=user_id)

        result_df, user_score = game_result(league_id, game_id, user_id)

        self.result_df = result_df
        self.user_score = user_score

        if result_df.filter(pl.col('user_id')==user_id).select('bet_perfect').item() == True:
            user_bet = 3 #Perfect
        elif result_df.filter(pl.col('user_id')==user_id).select('bet_correct').item() == True:
            user_bet = 2 #Correct
        elif result_df.filter(pl.col('user_id') == user_id).select('bet_exists').item() == True:
            user_bet = 1 #Exists
        else:
            user_bet = 0 #No Bet

        self.user_bet = user_bet

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