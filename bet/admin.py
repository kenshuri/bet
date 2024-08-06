from django.contrib import admin
from bet.models import Competition,League, Team, Game, Bet

# Register your models here.
admin.site.register(Competition)
admin.site.register(League)
admin.site.register(Team)
admin.site.register(Game)
admin.site.register(Bet)