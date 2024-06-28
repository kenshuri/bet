from django.contrib import admin
from bet.models import League, Team, Game, Bet

# Register your models here.
admin.site.register(League)
admin.site.register(Team)
admin.site.register(Game)
admin.site.register(Bet)