import datetime
from typing import Literal

from ninja import Schema

from api.schemas.auth import ActiveDivisionRef
from api.schemas.players import DivisionWonBadgeOut


class SeasonSummaryRef(Schema):
    id: int
    name: str
    year: int
    season_round: int
    start_date: datetime.date
    end_date: datetime.date
    is_draft: bool
    is_closed: bool


class SeasonStatsOut(Schema):
    divisions: int
    percentage_played: str
    total_games_count: int
    results_count: int
    player_count: int


class DivisionLeaderOut(Schema):
    division: int
    player: str
    player_id: int | None
    total: int | str
    played: float


class SeasonProgressOut(Schema):
    season_days: list[int]
    season_total_matches: list[int]
    played_days: list[int]
    played: list[int]
    played_cumulative: list[int]
    season_start: str
    today_day: int


class RecentMatchOut(Schema):
    winner_id: int
    winner_name: str
    loser_id: int
    loser_name: str
    winner_score: int
    loser_score: int
    score_display: str
    is_incomplete: bool
    is_injury: bool
    incomplete_reason: str | None
    division: int
    year: int
    season_round: int
    date_added: datetime.date
    date_display: str
    date_full: str


class MyDivisionSummaryOut(Schema):
    ladder_id: int
    division: int
    matches_played: int
    total_opponents: int
    total_points: int
    rank_in_division: int
    division_size: int
    is_closed: bool


class CurrentSeasonOverviewOut(Schema):
    season: SeasonSummaryRef
    stats: SeasonStatsOut
    leaders: list[DivisionLeaderOut]
    progress: SeasonProgressOut
    recent_results: list[RecentMatchOut]
    my_division: MyDivisionSummaryOut | None = None


class SeasonArchiveItemOut(Schema):
    id: int
    name: str
    year: int
    season_round: int
    start_date: datetime.date
    end_date: datetime.date
    divisions_count: int
    player_count: int
    total_matches: int
    matches_played: int
    completion_pct: float
    is_latest: bool


class SeasonArchiveSummaryOut(Schema):
    total_seasons: int
    total_divisions: int
    total_matches_played: int
    total_matches_scheduled: int
    overall_completion: str
    years_span: str


class SeasonListOut(Schema):
    seasons: list[SeasonArchiveItemOut]
    available_years: list[int]
    summary: SeasonArchiveSummaryOut


class GridCellOut(Schema):
    is_self: bool
    player_id: int
    opponent_id: int
    opponent_name: str | None = None
    result: int | None = None


class GridRowOut(Schema):
    position: int
    player_id: int
    player_name: str
    is_current_user: bool
    cells: list[GridCellOut]
    total: int
    average: str | int
    matches_played: int


class DivisionGridOut(Schema):
    ladder_id: int
    division: int
    ladder_type: str
    rows: list[GridRowOut]


class SeasonDetailOut(Schema):
    season: SeasonSummaryRef
    divisions: list[DivisionGridOut]


class DivisionLeaderStatOut(Schema):
    player_id: int
    player_name: str
    total: int
    played: int
    won: int
    lost: int
    retired: int
    incomplete: int
    avg: str
    max_possible: int


class DivisionStatsOut(Schema):
    players_count: int
    total_matches_played: int
    total_matches: int
    matches_remaining: int
    perc_matches_played: float
    leader: DivisionLeaderStatOut | None
    leaders: list[DivisionLeaderStatOut]
    avg_match_score: str | None
    avg_games_per_match: str | None
    total_games_played: int
    close_matches_count: int
    close_matches_pct: float


class DivisionDetailOut(Schema):
    season: SeasonSummaryRef
    ladder_id: int
    division: int
    ladder_type: str
    is_closed: bool
    subscribed: bool
    can_admin_enter: bool
    has_prev_division: bool
    has_next_division: bool
    grid: DivisionGridOut
    stats: DivisionStatsOut
    recent_results: list[RecentMatchOut]


class SubscriptionToggleOut(Schema):
    subscribed: bool
    detail: str


class OpponentQuickOut(Schema):
    id: int
    name: str
    h2h_played: int
    h2h_won: int
    h2h_lost: int


class EnteredMatchOut(Schema):
    pair_key: str
    opponent_id: int
    opponent_name: str
    winner_id: int
    loser_id: int
    my_score: int
    opp_score: int
    losing_score: int
    outcome_code: str
    is_incomplete: bool
    is_injury: bool
    incomplete_reason: str | None
    score_display: str
    date_added: datetime.date


class ResultEntryContextOut(Schema):
    has_active_ladder: bool
    ladder: ActiveDivisionRef | None
    player_id: int | None
    player_name: str | None
    is_closed: bool
    total_opponents: int
    unplayed: list[OpponentQuickOut]
    entered: list[EnteredMatchOut]


class SubmitResultIn(Schema):
    opponent_id: int
    outcome: Literal["won", "lost", "incomplete"]
    primary_score: int
    opponent_score: int | None = None
    incomplete_reason: Literal["time", "injury"] | None = None
    injured_player: Literal["opponent", "me"] | None = None


class EditResultIn(Schema):
    match_mode: Literal["completed", "time", "injury"]
    winner_id: int | None = None
    winner_score: int | None = None
    losing_score: int | None = None


class AdminSubmitResultIn(Schema):
    winner_id: int
    loser_id: int
    losing_score: int
    incomplete_reason: Literal["time", "injury"] | None = None


class ResultMutationOut(Schema):
    pair_key: str
    changed: bool = True
    detail: str


class ClubStatsFilterOut(Schema):
    filter_type: str
    period: str | None
    selected_year: int | None
    selected_season_id: int | None
    filter_label: str
    min_rounds: int


class SeasonFilterOptionOut(Schema):
    id: int
    name: str
    year: int
    season_round: int


class ClubStatsSummaryOut(Schema):
    seasons_count: int
    divisions_count: int
    matches_played: int
    active_players: int


class ClubPlayerMatchStatOut(Schema):
    player_id: int
    player_name: str
    played: int
    won: int
    lost: int
    retired: int
    incomplete: int
    total_points: int
    win_rate: float
    win_rate_display: str
    avg_points: float
    avg_points_display: str


class ClubPlayerStandingStatOut(Schema):
    player_id: int
    player_name: str
    best_centile: int
    best_rank: int
    best_total_players: int
    best_year: int
    best_round: int
    best_division: int
    peak_count: int
    avg_centile: float
    avg_centile_display: str
    seasons_played: int
    division_titles: int
    div1_titles: int
    title_rate: float
    title_rate_display: str
    divisions_won_badges: list[DivisionWonBadgeOut]
    scheduled_matches: int
    played_matches: int
    completion_rate: float
    completion_rate_display: str


class ClubRivalryStatOut(Schema):
    player_a_id: int
    player_a_name: str
    player_a_wins: int
    player_b_id: int
    player_b_name: str
    player_b_wins: int
    matches_played: int
    last_played: datetime.date | None


class ClubLeaderboardsOut(Schema):
    most_won: list[ClubPlayerMatchStatOut]
    most_played: list[ClubPlayerMatchStatOut]
    most_points: list[ClubPlayerMatchStatOut]
    most_titles: list[ClubPlayerStandingStatOut]
    highest_completion: list[ClubPlayerStandingStatOut]
    top_rivalries: list[ClubRivalryStatOut]
    best_centile: list[ClubPlayerStandingStatOut]


class ClubStatsOut(Schema):
    filter: ClubStatsFilterOut
    available_years: list[int]
    available_seasons: list[SeasonFilterOptionOut]
    summary: ClubStatsSummaryOut
    leaderboards: ClubLeaderboardsOut
    page_size: int
