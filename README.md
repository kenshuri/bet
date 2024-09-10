# Minimal template to set-up a Django project with TailwindCSS and daisyUI

As described, this code will set-up a Django Project with tailwindCSS and daisyUI. The auto-reload feature is also included.

The code for this was vastly inspired from a stackoverflow answer on [How to use TailwindCSS with Django?](https://stackoverflow.com/questions/63392426/how-to-use-tailwindcss-with-django#63392427). You can have a look ay my [blog post](https://blog.kenshuri.com/posts/001_setup_django_tailwind_daisyui.md) for some details.

## Set-up the project

To set-up the project from scratch, run the following commands in your terminal.

```shell
git clone https://github.com/kenshuri/setup_django_tailwind_daisyui.git
cd setup_django_tailwind_daisyui
python -m virtualenv venv
pip install -r requirements.txt
cd jstoolchains
npm install
```

You're good to go my friend!

## Start your project 

To see your project in action, open 2 terminals.

In the first terminal run:
```shell
cd setup_django_tailwind_daisyui
cd jstoolchains
npm run tailwind-watch
```

In the second terminal run:
```
cd setup_django_tailwind_daisyui
python manage.py runserver
```

As prompted, open the page http://127.0.0.1:8000/ and enjoy 🚀

Note that changes in your html template `blogApp\templates\blogApp\index.html` automatically updates what you see in your browser.


## When updatong o2switch next time

- first migrate 6
- then add a object in customuser table (to referenced a deleted owner later
0,0,,0,0,0,0,0,0,deleted

- add "deleted" object to competition
0,deleted,0


- run migrate 7


## Reimporting old data with SQLite Expert

- Attached db_new.sqlite3 to current db.sqlite3

Run SQL
```sql
INSERT INTO accounts_customuser SELECT * FROM db_new.accounts_customuser;
INSERT INTO bet_team SELECT * FROM db_new.bet_team;
INSERT INTO bet_competition SELECT * FROM db_new.bet_competition;
INSERT INTO bet_league SELECT * FROM db_new.bet_league;
INSERT INTO bet_league_users SELECT * FROM db_new.bet_league_users;
INSERT INTO bet_game (id, score_team1, score_team2, start_datetime, team_1_id, team_2_id, competition_number, game_type, score_team1_after_ext, score_team2_after_ext, competition_id) SELECT id, score_team1, score_team2, start_datetime, team_1_id, team_2_id, competition_number, game_type, score_team1_after_ext, score_team2_after_ext, competition_id FROM db_new.bet_game;
INSERT INTO bet_bet (id, score_team1, score_team2, user_id, league_id, game_id) SELECT id, score_team1, score_team2, user_id, league_id, game_id FROM db_new.bet_bet;
```

## Polars nuimber of rows
```python
import polars as pl
pl.Config(tbl_rows=100)
```