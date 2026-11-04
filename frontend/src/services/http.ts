import type { AnalyticalEnvelope } from "@/types/api";

const DEFAULT_API_BASE_URL = "";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiContractError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function assertAnalyticalEnvelope<T>(
  value: unknown,
): asserts value is AnalyticalEnvelope<T> {
  if (!isRecord(value)) {
    throw new ApiContractError("La API no devolvió un objeto analítico.");
  }
  const requiredKeys = ["data", "meta", "coverage", "warnings", "methodology"];
  if (!requiredKeys.every((key) => key in value)) {
    throw new ApiContractError("La respuesta no contiene el envelope analítico completo.");
  }
  if (
    !isRecord(value.meta) ||
    !isRecord(value.coverage) ||
    !Array.isArray(value.warnings) ||
    !Array.isArray(value.methodology)
  ) {
    throw new ApiContractError("La estructura del envelope analítico es inválida.");
  }
}

function buildUrl(path: string, params?: URLSearchParams): string {
  const baseUrl = (
    process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_API_BASE_URL
  ).replace(/\/$/, "");
  const query = params?.toString();
  return `${baseUrl}${path}${query ? `?${query}` : ""}`;
}

export async function getAnalyticalEnvelope<T>(
  path: string,
  params?: URLSearchParams,
  signal?: AbortSignal,
): Promise<AnalyticalEnvelope<T>> {
  const response = await fetch(buildUrl(path, params), {
    headers: { Accept: "application/json" },
    signal,
  });
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiContractError("La API devolvió una respuesta que no es JSON.");
  }
  if (!response.ok) {
    throw new ApiError(`La API respondió con estado ${response.status}.`, response.status, body);
  }
  assertAnalyticalEnvelope<T>(body);
  return body;
}
