import type { components } from "./schema";

export type ApiSchema<K extends keyof components["schemas"]> =
  components["schemas"][K];

export type ActiveDivisionRef = ApiSchema<"ActiveDivisionRef">;
export type UserMeOut = ApiSchema<"UserMeOut">;
export type TokenOut = ApiSchema<"TokenOut">;
export type AccountOut = ApiSchema<"AccountOut">;
export type SubscriptionRef = ApiSchema<"SubscriptionRef">;

export type SeasonSummaryRef = ApiSchema<"SeasonSummaryRef">;
export type SeasonStatsOut = ApiSchema<"SeasonStatsOut">;
export type DivisionLeaderOut = ApiSchema<"DivisionLeaderOut">;
export type SeasonProgressOut = ApiSchema<"SeasonProgressOut">;
export type RecentMatchOut = ApiSchema<"RecentMatchOut">;
export type MyDivisionSummaryOut = ApiSchema<"MyDivisionSummaryOut">;
export type CurrentSeasonOverviewOut = ApiSchema<"CurrentSeasonOverviewOut">;
export type SeasonArchiveItemOut = ApiSchema<"SeasonArchiveItemOut">;
export type SeasonListOut = ApiSchema<"SeasonListOut">;
export type GridCellOut = ApiSchema<"GridCellOut">;
export type GridRowOut = ApiSchema<"GridRowOut">;
export type DivisionGridOut = ApiSchema<"DivisionGridOut">;
export type SeasonDetailOut = ApiSchema<"SeasonDetailOut">;
export type DivisionStatsOut = ApiSchema<"DivisionStatsOut">;
export type DivisionDetailOut = ApiSchema<"DivisionDetailOut">;

export type OpponentQuickOut = ApiSchema<"OpponentQuickOut">;
export type EnteredMatchOut = ApiSchema<"EnteredMatchOut">;
export type ResultEntryContextOut = ApiSchema<"ResultEntryContextOut">;
export type SubmitResultIn = ApiSchema<"SubmitResultIn">;
export type EditResultIn = ApiSchema<"EditResultIn">;

export type PlayerAutocompleteOption = ApiSchema<"PlayerAutocompleteOption">;
export type PlayerProfileOut = ApiSchema<"PlayerProfileOut">;
export type PlayerH2HSummaryOut = ApiSchema<"PlayerH2HSummaryOut">;
export type PlayerSeasonHistoryOut = ApiSchema<"PlayerSeasonHistoryOut">;
export type CentilePointOut = ApiSchema<"CentilePointOut">;
export type HeadToHeadOut = ApiSchema<"HeadToHeadOut">;
export type H2HMatchOut = ApiSchema<"H2HMatchOut">;

export type ClubStatsOut = ApiSchema<"ClubStatsOut">;
export type ClubPlayerMatchStatOut = ApiSchema<"ClubPlayerMatchStatOut">;
export type ClubPlayerStandingStatOut = ApiSchema<"ClubPlayerStandingStatOut">;
export type ClubRivalryStatOut = ApiSchema<"ClubRivalryStatOut">;
