import plistlib

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.db.models import Q

import polars as pl
from silk.profiling.profiler import silk_profile

from accounts.forms import CustomUserCreationForm
from bet.forms import SignUpForm, BetForm, LeagueForm, CompetitionForm, GameForm, TeamForm
from bet.models import Game, Bet, CustomUser, League, Competition, Team, ActivityType, GameType
from django.utils import timezone
from bet.utils import get_table, get_game_results, Result, Ranking, get_predictions, get_leagues, get_results, get_results_as_user



# Create your views here.
@login_required
def index(request):
    user = CustomUser.objects.get(id=request.user.id)
    predictions = get_predictions(request.user.id)
    if predictions.shape[0] !=0:
        predictions_next = predictions.filter(pl.col('start_datetime') > timezone.now()).sort('start_datetime').head(3)
    else:
        predictions_next = predictions
    results = get_results_as_user(request.user.id)
    if results.shape[0] !=0:
        results_last = results.sort('start_datetime', 'league_id', descending=[True, False]).head(3)
    else:
        results_last = results

    context = {
        'first_name': user.first_name,
        'predictions_json': predictions_next.write_json(),
        'results_json': results_last.write_json(),
        'user_id': request.user.id,
    }
    return render(request, 'bet/index.html', context=context)


@login_required
def leagues_legacy(request):
    all_leagues = League.objects.filter(id=1)
    user_leagues = League.objects.filter(users=request.user)
    rankings = list()
    for league in user_leagues:
        rankings.append(Ranking(user_id=request.user.id, league_id=league.id))

    table_df = get_table()
    context = {
        'all_leagues': all_leagues,
        'user_leagues': user_leagues,
        'league_id': 1,
        'table_dict': table_df.to_dicts(),
        'rankings': rankings,
    }
    return render(request, 'bet/leagues_legacy.html', context=context)


@login_required
def predictions(request):
    data = get_predictions(request.user.id)
    results = get_results_as_user(request.user.id)
    context = {
        'predictions_json': data.write_json(),
        'results_json': results.write_json(),
        'user_id': request.user.id,
    }
    return render(request, "bet/predictions.html", context=context)

def leagues(request):
    leagues_df = get_leagues(request.user.id)
    leagues = [{
        'league_id': league.item(0, 'league_id'),
        'league__name': league.item(0, 'league__name'),
        'league__short_name': league.item(0, 'league__short_name'),
        'competition_id': league.item(0, 'competition_id'),
        'competition__name': league.item(0, 'competition__name'),
        'competition__short_name': league.item(0, 'competition__short_name'),
        'league_details': league.sort(
            'total_points', 'first_name', 'user_id', descending=[True, False, False]
        ).with_columns(
            pl.col('total_points').rank(method='ordinal', descending=True).alias('user_rank_ordinal'),
            pl.col('total_points').rank(method='min', descending=True).alias('user_rank'),
        ).filter(
            (pl.col('user_rank_ordinal').is_in([1,2,3]) | (pl.col('user_id') == request.user.id))
        ).select(
            'user_rank', 'user_id', 'first_name', 'bet_exists_count', 'bet_ok_count', 'bet_perfect_count', 'total_points'
        ).to_dicts(),
    } for league in leagues_df]
    context = {
        'leagues': leagues,
    }
    return render(request, "bet/leagues.html", context=context)


@login_required
def league(request, league_id:int):
    #TODO: check case where league exist but no game defined on the league
    predictions = get_predictions(request.user.id).filter(league_id=league_id)
    results = get_results_as_user(request.user.id).filter(league_id=league_id)
    leagues_df = get_leagues(request.user.id)
    league_list = [{
        'league_id': league.item(0, 'league_id'),
        'league__name': league.item(0, 'league__name'),
        'league__short_name': league.item(0, 'league__short_name'),
        'leagues_played__bonus_perfect': league.item(0, 'leagues_played__bonus_perfect'),
        'leagues_played__bonus_stake': league.item(0, 'leagues_played__bonus_stake'),
        'leagues_played__with_ext': league.item(0, 'leagues_played__with_ext'),
        'competition_id': league.item(0, 'competition_id'),
        'competition__name': league.item(0, 'competition__name'),
        'competition__short_name': league.item(0, 'competition__short_name'),
        'league_details': league.sort(
            'total_points', 'first_name', 'user_id', descending=[True, False, False]
        ).with_columns(
            pl.col('total_points').rank(method='ordinal', descending=True).alias('user_rank_ordinal'),
            pl.col('total_points').rank(method='min', descending=True).alias('user_rank'),
        ).select(
            'user_rank', 'user_id', 'first_name', 'bet_exists_count', 'bet_ok_count', 'bet_perfect_count',
            'total_points',
        ).to_dicts(),
    } for league in leagues_df if league.item(0, 'league_id') == league_id]
    if len(league_list) > 0:
        league = league_list[0]
    else:
        l = League.objects.filter(id=league_id).values(
            'id', 'name', 'short_name',
            'bonus_perfect', 'bonus_stake', 'with_ext',
            'competition_id','competition__name', 'competition__short_name',
        )
        if l.exists():
            l_df = pl.from_records(list(l)).rename({
                'id': 'league_id',
                'name': 'league__name',
                'short_name': 'league__short_name',
                'bonus_perfect': 'leagues_played__bonus_perfect',
                'bonus_stake': 'leagues_played__bonus_stake',
                'with_ext': 'leagues_played__with_ext',

            })
            users = CustomUser.objects.filter(leagues_played=l_df.item(0, 'league_id')).values('id', 'first_name')
            if users.exists():
                users_df = pl.from_records(list(users)).rename({
                    'id': 'user_id',
                }).with_columns(
                    pl.lit(l_df.item(0, 'league_id')).cast(pl.Int64).alias('league_id'),
                    pl.lit(0).alias('bet_exists_count'),
                    pl.lit(0).alias('bet_ok_count'),
                    pl.lit(0).alias('bet_perfect_count'),
                    pl.lit(0).alias('total_points'),
                )
                league_data = l_df.join(users_df, how='left', on='league_id')
                league = {
                    'league_id': league_data.item(0, 'league_id'),
                    'league__name': league_data.item(0, 'league__name'),
                    'league__short_name': league_data.item(0, 'league__short_name'),
                    'leagues_played__bonus_perfect': league_data.item(0, 'leagues_played__bonus_perfect'),
                    'leagues_played__bonus_stake': league_data.item(0, 'leagues_played__bonus_stake'),
                    'leagues_played__with_ext': league_data.item(0, 'leagues_played__with_ext'),
                    'competition_id': league_data.item(0, 'competition_id'),
                    'competition__name': league_data.item(0, 'competition__name'),
                    'competition__short_name': league_data.item(0, 'competition__short_name'),
                    'league_details': league_data.sort(
                        'total_points', 'first_name', 'user_id', descending=[True, False, False]
                    ).with_columns(
                        pl.col('total_points').rank(method='ordinal', descending=True).alias('user_rank_ordinal'),
                        pl.col('total_points').rank(method='min', descending=True).alias('user_rank'),
                    ).select(
                        'user_rank', 'user_id', 'first_name', 'bet_exists_count', 'bet_ok_count', 'bet_perfect_count',
                        'total_points',
                    ).to_dicts()
                }

            else:
                league = None

        else:
            league = None

    if league is not None:
        league_exists = True
    else:
        league_exists = False
    context = {
        'league_exists': league_exists,
        'predictions_json': predictions.write_json(),
        'results_json': results.write_json(),
        'league': league,
        'user_id': request.user.id,
    }
    return render(request, "bet/league.html", context=context)


@login_required
def rankings(request):
    all_leagues = League.objects.filter(id=1)
    user_leagues = League.objects.filter(users=request.user)
    rankings = list()
    for league in user_leagues:
        rankings.append(Ranking(user_id=request.user.id, league_id=league.id))

    table_df = get_table()
    context = {
        'all_leagues': all_leagues,
        'user_leagues': user_leagues,
        'league_id': 1,
        'table_dict': table_df.to_dicts(),
        'rankings': rankings,
    }
    return render(request, 'bet/rankings.html', context=context)





@login_required
def bets(request):
    user_leagues = League.objects.filter(users=request.user).values('id').distinct()
    user_competitions = League.objects.filter(users=request.user).values('competition_id').distinct()
    # league = League.objects.all()[:1].get()
    # league_id = league.id
    upcoming_games = Game.objects.filter(start_datetime__gt=timezone.now()).filter(competition__in=user_competitions).order_by('start_datetime')
    existing_bets = Bet.objects.filter(user=request.user).filter(league__in=user_leagues).filter(game__in=upcoming_games)
    # upcoming_games_list = list(upcoming_games.values_list('id', flat=True))
    user_leagues_list = list(user_leagues.values_list('id', flat=True))
    upcoming_bets = list()
    for league_id in user_leagues_list:
        user_lg_competition = League.objects.filter(id=league_id).values('competition_id').distinct()
        upcoming_games_lg = Game.objects.filter(start_datetime__gt=timezone.now()).filter(competition__in=user_lg_competition).order_by('start_datetime')
        upcoming_games_lg_list = list(upcoming_games_lg.values_list('id', flat=True))
        for game_id in upcoming_games_lg_list:
            if existing_bets.filter(game=game_id).filter(league=league_id).exists():
                # Create a Bet form based on values of existing Bet
                bet_form = BetForm(instance=existing_bets.get(game=game_id, league=league_id))
            else:
                # Create a new Bet form using the information in Game & League
                game = get_object_or_404(Game, pk=game_id)
                league = get_object_or_404(League, pk=league_id)
                bet_form = BetForm(instance=Bet(
                    game = game,
                    league = league,
                    user = request.user,
                ))
            upcoming_bets.append(bet_form)
    upcoming_bets_sorted = upcoming_bets.sort(key=lambda x: (x.instance.game.start_datetime,
                                                             x.instance.game.competition.id,
                                                             x.instance.league.id))
    context = {
        # 'upcoming_games': upcoming_games_list,
        'existing_bets': existing_bets,
        'upcoming_bets': upcoming_bets,
        'user_leagues': user_leagues}
    return render(request, 'bet/bets.html', context=context)

@login_required
def place_bet(request):
    if request.method == 'POST':
        form = BetForm(request.POST)
        if form.is_valid():
            game = form.cleaned_data['game']
            if game.start_datetime < timezone.now():
                print('Game already started')
                return redirect('bets')
            else:
                bet, created = Bet.objects.update_or_create(
                    user=request.user,
                    game=form.cleaned_data['game'],
                    league=form.cleaned_data['league'],
                    defaults={
                        'score_team1': form.cleaned_data['score_team1'],
                        'score_team2': form.cleaned_data['score_team2']
                    }
                )
                return render(request, 'bet/partials/bet_placed.html', context={'bet': bet, 'created': created})
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    print(f'Error in {field_name}: {error}')
    else:
        form = BetForm()
    context = {'form': form}
    return render(request, 'bet/bets.html', context=context)



@silk_profile(name='View Results')
@login_required
def results(request):
    """
    For each each league, get the competition, then all games started for this competition, and finally, for each game/compet/league, compute the results

    The HTML template requires:
    - list of all league/competition/game & result
    Parameters
    ----------
    request

    Returns
    -------

    """
    user_leagues = League.objects.filter(users=request.user)
    user_leagues_list = list(user_leagues.values_list('id', flat=True))
    results = list()
    for league_id in user_leagues_list:
        user_lg_competition = League.objects.filter(id=league_id).values('competition_id').distinct()
        started_games_lg = Game.objects.filter(start_datetime__lt=timezone.now()).filter(competition__in=user_lg_competition).order_by('-start_datetime')
        started_games_lg_list = list(started_games_lg.values_list('id', flat=True))
        for game_id in started_games_lg_list:
            results.append(Result(league_id, game_id, request.user.id))

    games = Game.objects.filter(start_datetime__lt=timezone.now()).order_by('-start_datetime')
    bets_dict = dict()
    for game in games:
        bets_dict[game.id] = get_game_results(game.id).to_dicts()
    context = {'bets_dict': bets_dict,
               'games': games,
               'user_leagues':user_leagues,
               'results': results}
    return render(request, 'bet/results.html', context=context)

@login_required
def leagues_config(request):
    leagues_played = League.objects.filter(users = request.user)
    leagues_created = League.objects.filter(owner=request.user)
    return render(request, 'bet/leagues_config.html', {'leagues': leagues_played,
                                                'leagues_created': leagues_created,
                                                'leagues_played': leagues_played
                                                       })


@login_required
def create_league(request):
    if request.method == 'POST':
        form = LeagueForm(request.POST)
        if form.is_valid():
            league = form.save(commit=False)
            league.owner = request.user
            league.save()
            return redirect('leagues')
    else:
        form = LeagueForm()
        c_choices = Competition.objects.exclude(id=0)
    return render(request, 'bet/create_league.html',
                  {'form': form, 'ln': request.GET['league_name'], 'c_choices': c_choices})


#TODO: Feature "Update League"


@login_required
def create_competition(request):
    if request.method == 'POST':
        form = CompetitionForm(request.POST)
        if form.is_valid():
            competition = form.save(commit=False)
            competition.owner = request.user
            competition.save()
        return redirect('competitions')
    else:
        form = CompetitionForm()
        a_choices = ActivityType
        return render(request, 'bet/create_competition.html',
                      {'form': form, 'ln': request.GET.get('competition_name', ''),
                       'a_choices': a_choices})


@login_required
def create_game(request):
    if request.method == 'POST':
        form = GameForm(request.POST)
        game_created_flag = 1
        if form.is_valid():
            game = form.save(commit=False)
            if game.competition.owner == request.user:
                game.save()
                game_created_flag = 2
        competitions_created = Competition.objects.filter(owner=request.user)
        games_owner = Game.objects.filter(competition__owner=request.user)
        games = list()
        for g in games_owner:
            game_form = GameForm(instance=g)
            games.append(game_form)
        return render(request, 'bet/competitions.html',
                      {'competitions_created': competitions_created, 'games': games,
                       'game_created_flag': game_created_flag})
    else:
        # CAREFUL - Anything updated here should also be updated in create_team code
        game_form = GameForm()
        c = Competition.objects.get(id=request.GET.get('competition_id'))
        if c.activity_type == ActivityType.MIXED:
            t_choices = Team.objects.filter(Q(owner=request.user) | Q(owner__is_staff=True))
            a_choices = ActivityType
        else:
            t_choices = Team.objects.filter(activity_type__in=[0, c.activity_type]).filter(Q(owner=request.user) | Q(owner__is_staff=True))
            a_choices = [{'label': 'Needed to deal with MIXED Activity', 'value': 0},
                         {'label': [ca[1] for ca in ActivityType.choices if ca[0] == c.activity_type][0],
                          'value': c.activity_type}]
        gt_choices = GameType
        return render(request, 'bet/create_game.html',
                      {'game_form': game_form, 'c': c, 't_choices': t_choices, 'a_choices': a_choices, 'gt_choices': gt_choices})


@login_required
def update_game(request):
    if request.method == 'POST':
        game = Game.objects.get(id=request.POST.get('game_id'))
        form = GameForm(request.POST, instance=game)
        game_updated_flag = False
        if form.is_valid():
            form.save()
            game_updated_flag = True
        return render(request, 'bet/partials/game_updated.html', context={'game_updated_flag': game_updated_flag, 'game': game})

    return redirect('competitions')



@login_required
def competitions(request):
    competitions_created = Competition.objects.filter(owner=request.user)
    games_owner = Game.objects.filter(competition__owner=request.user).order_by('-start_datetime', 'competition_id')
    games = list()
    for g in games_owner:
        game_form = GameForm(instance=g)
        games.append(game_form)

    return render(request, 'bet/competitions.html', {'competitions_created': competitions_created, 'games': games})


@login_required
def teams(request):
    teams_created = Team.objects.filter(owner=request.user)
    games_linked = Game.objects.filter(Q(team_1__in=teams_created) | Q(team_2__in=teams_created))
    competitions_linked = Competition.objects.filter(id__in=games_linked.values('competition')).distinct()
    return render(request, 'bet/teams.html', {'teams_created': teams_created, 'competitions_linked': competitions_linked})


def create_team(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            form = form.save(commit=False)
            form.owner = request.user
            form.save()
            team_created_flag = True
        else:
            team_created_flag = False
        # CAREFUL - Anything updated here should also be updated in create_game code
        c_id = request.POST.get('team_competition_id')
        game_form = GameForm()
        c = Competition.objects.get(id=c_id)
        if c.activity_type == ActivityType.MIXED:
            t_choices = Team.objects.filter(Q(owner=request.user) | Q(owner__is_staff=True))
            a_choices = ActivityType
        else:
            t_choices = Team.objects.filter(activity_type__in=[0, c.activity_type]).filter(Q(owner=request.user) | Q(owner__is_staff=True))
            a_choices = [{'label': 'Needed to deal with MIXED Activity', 'value': 0},
                         {'label': [ca[1] for ca in ActivityType.choices if ca[0] == c.activity_type][0],
                          'value': c.activity_type}]
        gt_choices = GameType
        return render(request, 'bet/partials/create_game_teams.html',
                      {'game_form': game_form, 'c': c, 't_choices': t_choices, 'a_choices': a_choices, 'gt_choices': gt_choices,
                       'team_created_flag': team_created_flag})


#TODO: Update Team feature



def join_league(request):
    if request.method == 'POST':
        league_code = request.POST['league_code']
        league_qs = League.objects.filter(code=league_code)
        if len(league_qs) == 1:
            league = league_qs.get()
            league.users.add(request.user)
    return redirect('leagues')

def quit_league(request, league_id):
    league = get_object_or_404(League, pk=league_id)
    league.users.remove(request.user)
    return redirect('leagues')

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get('email')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(email=email, password=raw_password)
            login(request, user)
            return redirect("index")
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})