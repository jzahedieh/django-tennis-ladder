import datetime

from ninja import Schema


class PlayerAutocompleteOption(Schema):
    id: int
    label: str
    subtext: str


class PlayerSearchOut(Schema):
    options: list[PlayerAutocompleteOption]


class DivisionWonBadgeOut(Schema):
    division: int
    count: int
    is_div1: bool
    label: str


class CentilePointOut(Schema):
    league_id: int
    season_label: str
    season_name: str
    division: int
    rank: int
    total_players: int
    centile: int


class PlayerRecentMatchOut(Schema):
    won: bool
    outcome_code: str
    is_incomplete: bool
    is_injury: bool
    my_games: int
    opp_games: int
    score_display: str
    opponent_id: int
    opponent_name: str
    date_added: datetime.date
    season_label: str


class PlayerH2HSummaryOut(Schema):
    opponent_id: int
    opponent_name: str
    times_played: int
    won: int
    lost: int
    retired: int
    incomplete: int
    win_rate: float
    win_rate_display: str
    won_played_display: str
    last_played: datetime.date | None


class PlayerCareerStatsOut(Schema):
    played: int | str
    win_rate: str
    completion_rate: str = "- %"
    average: str
    best_centile: str
    avg_centile: str
    seasons_played: int
    division_titles: int
    divisions_won_badges: list[DivisionWonBadgeOut]
    highest_division: int | str
    scheduled_matches: int
    first_year: int | None
    last_year: int | None
    best_rank: int | None
    best_total_players: int | None
    best_season_label: str | None
    won: int
    lost: int
    retired: int
    incomplete: int
    total_points: int
    unique_opponents: int


class PlayerInsightsOut(Schema):
    has_matches: bool
    recent_form: list[PlayerRecentMatchOut]
    longest_win_streak: int
    current_win_streak: int
    full_completion_rounds: int
    full_completion_rate: str
    best_round_points: int
    best_round_label: str | None
    clutch_played: int
    clutch_won: int
    clutch_lost: int
    clutch_win_rate: str
    dominant_wins: int
    bagels_won: int
    total_games_won: int
    total_games_lost: int
    games_win_rate: str
    avg_loser_score_in_wins: str
    avg_player_score_in_losses: str
    most_played_rival: PlayerH2HSummaryOut | None
    favourite_rival: PlayerH2HSummaryOut | None
    toughest_rival: PlayerH2HSummaryOut | None


class PlayerSeasonHistoryOut(Schema):
    league_id: int
    season_id: int
    season_name: str
    year: int
    season_round: int
    division: int
    total_points: float
    games: int
    scheduled_matches: int
    points_per_game: float
    won_count: int
    pct_played: float
    is_division_winner: bool
    centile: int | None
    rank: int | None
    total_players: int | None


class PlayerProfileOut(Schema):
    player_id: int
    player_name: str
    is_authenticated_view: bool
    stats: PlayerCareerStatsOut
    insights: PlayerInsightsOut
    centile_chart_data: list[CentilePointOut]
    head_to_head: list[PlayerH2HSummaryOut]
    season_history: list[PlayerSeasonHistoryOut]


class H2HMatchOut(Schema):
    date_added: datetime.date
    year: int
    season_round: int
    division: int
    ladder_full: str
    ladder_short: str
    player_won: bool
    is_incomplete: bool
    is_injury: bool
    winner_badge: str
    loser_badge: str
    winner_id: int
    winner_name: str
    loser_id: int
    loser_name: str
    winner_score: int
    losing_score: int
    player_score: int
    opponent_score: int
    score_display: str
    is_close: bool


class H2HStatsOut(Schema):
    played: int
    won: int
    lost: int
    retired: int
    incomplete: int
    player_win_pct: int
    opponent_win_pct: int
    player_games: int
    opponent_games: int
    close_matches: int
    first_played: datetime.date | None
    last_played: datetime.date | None


class HeadToHeadOut(Schema):
    player_id: int
    player_name: str
    opponent_id: int
    opponent_name: str
    stats: H2HStatsOut
    matches: list[H2HMatchOut]
