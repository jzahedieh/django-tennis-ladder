import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import React, { useEffect } from "react";

import { apiClient, extractApiError } from "../src/api/client";
import { useAuth } from "../src/auth/AuthContext";
import { ErrorState, LoadingState, PageScroll } from "../src/components/ui";

export default function CurrentLadderRedirectScreen() {
  const router = useRouter();
  const { user } = useAuth();

  const { data, error, refetch } = useQuery({
    queryKey: ["current-overview", user?.id ?? "anon"],
    queryFn: async () => {
      const { data, error } = await apiClient.GET(
        "/v1/ladder/seasons/current/overview"
      );
      if (error || !data) {
        throw new Error(extractApiError(error, "Could not load current ladder."));
      }
      return data;
    },
  });

  useEffect(() => {
    if (data?.season) {
      router.replace(`/${data.season.year}/round/${data.season.season_round}`);
    }
  }, [data, router]);

  if (error) {
    return (
      <PageScroll>
        <ErrorState
          message={(error as Error)?.message || "Could not load current ladder."}
          onRetry={() => void refetch()}
        />
      </PageScroll>
    );
  }

  return (
    <PageScroll>
      <LoadingState label="Loading current ladder..." />
    </PageScroll>
  );
}
