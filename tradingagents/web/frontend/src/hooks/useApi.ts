// Custom hook for API calls with loading/error state

import { useState, useCallback } from "react";
import type { ApiResponse } from "../types";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>() {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const execute = useCallback(
    async (apiCall: () => Promise<ApiResponse<T>>) => {
      setState({ data: null, loading: true, error: null });
      try {
        const response = await apiCall();
        if (response.success && response.data !== null) {
          setState({ data: response.data, loading: false, error: null });
          return response.data;
        } else {
          setState({
            data: null,
            loading: false,
            error: response.error || "Unknown error",
          });
          return null;
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Network error";
        setState({ data: null, loading: false, error: msg });
        return null;
      }
    },
    []
  );

  return { ...state, execute };
}
