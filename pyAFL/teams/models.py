from bs4 import BeautifulSoup
import pandas as pd

from pyAFL.base.exceptions import LookupError
from pyAFL.players.models import Player
from pyAFL.requests import requests


class Team(object):
    """
    A class to represent an AFL Team.

    Attributes
    ----------
    name : str
        team full name.
    players : list
        list of all time players who played for the team (pyAFL player objects).
    games : Pandas DataFrame
        dataframe containing results of all games played by the team.

    """

    def __init__(self, name: str, url_identifier: str):
        """
        Constructs the Team object.

        Parameters
        ----------
            name : str (required)
                name of the person in format "[first] [last]"
            url_identifier : str (required)
                string parameter used in AFLtables URLs to identify team. Note that the naming convention changes from team to team
                Examples: - for Adelaide: url_identifier = "adelaide" (see https://afltables.com/afl/stats/teams/adelaide.html)
                          - for Greater Western Sydney: url_identifier = "gws" (see https://afltables.com/afl/stats/teams/gws.html)
                          - for Western Bulldogs: url_identifier = "bullldogs" (see https://afltables.com/afl/stats/teams/bullldogs.html)

        """

        self.name = name.title()  # Convert to title case for URL string matching
        self.all_time_players_url = f"https://afltables.com/afl/stats/teams/{url_identifier}.html"  # URL for all-time-players stats
        self.all_time_games_url = f"https://afltables.com/afl/teams/{url_identifier}/allgames.html"  # URL to all-time-games stats

    @property
    def players(self):
        """
        NB - a network request will be made when this class property is called.
        """

        return self._get_players()

    def _get_players(self):
        """
        Returns a list of pyAFL.Player objects for all players contained in `self.all_time_players_url`

        Returns
        ----------
            players : list
                list of pyAFL.Player objects

        """
        resp = requests.get(self.all_time_players_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        player_table = soup.find("table")
        player_table_body = player_table.find("tbody")
        player_anchor_tags = player_table_body.findAll("a")

        players = [
            Player(player.text, url=player.attrs.get("href"))
            for player in player_anchor_tags
        ]

        return players

    def season_stats(self, year: int):
        """
        Returns a Pandas dataframe detailing the season stats for the specified year.
        E.g. for Adelaide the table found at https://afltables.com/afl/stats/2020.html#1

        Parameters
        ----------
            year : int (required)
                year as a four-digit integer (e.g. 2019)

        Returns
        ----------
            season_stats : Pandas dataframe
                dataframe summarising individual player (and team total) stats for the specified year.

        """
        season_player_stats_url = f"https://afltables.com/afl/stats/{year}.html"
        resp = requests.get(season_player_stats_url)

        if resp.status_code == 404:
            raise Exception(f"Could not find season stats for year: {year}")

        soup = BeautifulSoup(resp.text, "html.parser")
        team_tables = soup.findAll("table")

        for table in team_tables:
            if table.find("th"):
                if self.name in table.find("th").text:
                    df = pd.read_html(str(table))

        if df is None:
            raise LookupError(
                f"Could not find season stats table for team {self.name} in year {year} at URL https://afltables.com/afl/stats/{year}.html"
            )

        season_stats = df[0]
        season_stats.columns = season_stats.columns.droplevel()

        return season_stats

    @property
    def games(self):
        return self._get_games()

    def _get_games(self):
        """
        Returns a Pandas dataframe listing every match contained in `self.all_time_games_url`

        Returns
        ----------
            games : Pandas dataframe
                dataframe listing all games played by the team. Contains results and match metadata.

        """
        resp = requests.get(self.all_time_games_url)
        soup = BeautifulSoup(resp.text, "html.parser")

        seasons = soup.findAll("table")

        dfs = []
        for season_html in seasons:
            df = pd.read_html(str(season_html))[0]
            df.columns = df.columns.droplevel(1)
            dfs.append(df)

        games = pd.concat(dfs)
        games = games.iloc[0:-2, :]
        games.index = pd.to_datetime(games.Date)

        games = games.rename(
            columns={"A": "Against", "F": "For", "R": "Result", "M": "Margin"}
        )

        return games
