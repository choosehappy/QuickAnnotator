import { useRef, useCallback } from "react"

/**
 * A custom hook that provides a mechanism to manage and guard asynchronous calls,
 * ensuring that only the latest call's result is processed.
 *
 * This is useful in scenarios where you want to prevent race conditions or
 * handle stale data from outdated asynchronous calls.
 *
 * @returns An object containing:
 * - `startCall`: A function to initiate a new asynchronous call and generate a unique token.
 * - `guard`: A function that takes a call token and returns a guarded asynchronous function.
 *
 * @example
 * ```typescript
 * const { startCall, guard } = useAsyncGuard();
 * 
 * const handleAsyncOperation = async () => {
 *   const callToken = startCall();
 *   const guardedFn = guard(callToken);
 * 
 *   await guardedFn(async () => {
 *     const data = await fetchData();
 *     setData(data);
 *   });
 * };
 * ```
 */
export function useAsyncGuard() {
  const activeCallRef = useRef(0)

  const startCall = useCallback(() => {
    activeCallRef.current += 1
    return activeCallRef.current
  }, [])

  const guard = useCallback((callToken: number) => {
    return async (fn: () => Promise<any>) => {
      if (callToken !== activeCallRef.current) return
      const result = await fn()
      if (callToken !== activeCallRef.current) return
      return result
    }
  }, [])

  return { startCall, guard }
}
