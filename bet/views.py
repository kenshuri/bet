from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from bet.forms import SignUpForm, BetForm
from bet.models import Game, Bet, CustomUser, League
from django.utils import timezone
from bet.utils import get_table

# Create your views here.
@login_required()
def index(request):
    # all_leagues = League.objects.all()
    all_leagues = League.objects.filter(pk=1)
    user_leagues = League.objects.filter(users=request.user)
    table_df = get_table()
    context = {
        'all_leagues': all_leagues,
        'user_leagues': user_leagues,
        'league_id': 1,
        'table_dict': table_df.to_dicts(),
    }
    return render(request, 'bet/index.html', context=context)

@login_required
def bets(request):
    user_leagues = League.objects.filter(users=request.user)
    league_id = 1
    upcoming_games = list(Game.objects.filter(start_datetime__gt=timezone.now()).order_by('start_datetime').values_list('pk', flat=True))
    existing_bets = Bet.objects.filter(league_id=league_id).filter(user=request.user).filter(game__in=upcoming_games)
    upcoming_bets = list()
    for game_id in upcoming_games:
        if game_id in existing_bets.values_list('game_id', flat=True):
            # Create a Bet form based on values of existing Bet
            bet_form = BetForm(instance=existing_bets.get(game_id=game_id))
        else:
            # Create a new Bet form using the information in Game
            game = get_object_or_404(Game, pk=game_id)
            league = get_object_or_404(League, pk=league_id)
            bet_form = BetForm(instance=Bet(
                game = game,
                league = league,
                user = request.user,
            ))
        upcoming_bets.append(bet_form)
    context = {'upcoming_games': upcoming_games,
               'existing_bets': existing_bets,
               'upcoming_bets': upcoming_bets,
               'user_leagues': user_leagues}
    return render(request, 'bet/bets.html', context=context)

@login_required
def place_bet(request):
    print('inside place_bet function')
    print(request.POST)
    print(request.method)
    if request.method == 'POST':
        print('inside place_bet function after POST check')
        form = BetForm(request.POST)
        print(form.is_valid())
        if form.is_valid():
            print('form is valid')
            bet, created = Bet.objects.update_or_create(
                user=request.user,
                game=form.cleaned_data['game'],
                league=form.cleaned_data['league'],
                defaults={
                    'score_team1': form.cleaned_data['score_team1'],
                    'score_team2': form.cleaned_data['score_team2']
                }
            )
            return redirect("bets", league_id=1)
        else:
            print('form is invalid')
            for field_name, errors in form.errors.items():
                for error in errors:
                    print(f'Error in {field_name}: {error}')
    else:
        form = BetForm()
    context = {'form': form}
    return render(request, 'bet/bets.html', context=context)


@login_required
def leagues(request):
    all_leagues = League.objects.all()
    return render(request, 'bet/leagues.html', {'leagues': all_leagues})

def join_league(request, league_id):
    league = get_object_or_404(League, pk=league_id)
    league.users.add(request.user)
    return redirect('index')

def quit_league(request, league_id):
    league = get_object_or_404(League, pk=league_id)
    league.users.remove(request.user)
    return redirect('leagues')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
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