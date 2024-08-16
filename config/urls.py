"""blogProject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

import bet.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', bet.views.index, name='index'),
    path('rankings', bet.views.rankings, name='rankings'),
    path('bets', bet.views.bets, name='bets'),
    path('place_bet', bet.views.place_bet, name='place_bet'),
    path('leagues', bet.views.leagues, name='leagues'),
    path('create_league', bet.views.create_league, name='create_league'),
    path('competitions', bet.views.competitions, name='competitions'),
    path('create_competition', bet.views.create_competition, name='create_competition'),
    path('create_game', bet.views.create_game, name='create_game'),
    path('update_game', bet.views.update_game, name='update_game'),
    path('teams', bet.views.teams, name='teams'),
    path('create_team', bet.views.create_team, name='create_team'),
    path('results', bet.views.results, name='results'),
    path('join_league', bet.views.join_league, name='join_league'),
    path('quit_league/<int:league_id>', bet.views.quit_league, name='quit_league'),
    path('__reload__/', include('django_browser_reload.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', bet.views.signup, name='signup'),
]
