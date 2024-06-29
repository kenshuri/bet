from bet.models import Game, Bet
from accounts.models import CustomUser
import polars as pl

def compute_result(score1: int, score2: int):
    if score1 > score2:
        return "W"
    elif score1 < score2:
        return "L"
    else:
        return "D"


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