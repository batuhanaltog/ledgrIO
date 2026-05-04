import { describe, it, expect } from "vitest";
import axios from "axios";
import { parseApiError } from "./errors";

function axiosErr(status: number, data: unknown) {
  return Object.assign(new axios.AxiosError("err"), {
    isAxiosError: true,
    response: { status, data, statusText: "", headers: {}, config: {} },
    config: {},
  });
}

describe("parseApiError", () => {
  it("flattens validation envelope into fieldErrors", () => {
    const err = axiosErr(400, {
      error: {
        type: "VALIDATION_ERROR",
        status: 400,
        detail: { email: ["already in use"], password: ["too short"] },
      },
    });
    const parsed = parseApiError(err);
    expect(parsed.type).toBe("VALIDATION_ERROR");
    expect(parsed.status).toBe(400);
    expect(parsed.fieldErrors).toEqual({
      email: "already in use",
      password: "too short",
    });
  });

  it("falls back to status-derived type when envelope is absent", () => {
    const err = axiosErr(404, { detail: "not found" });
    const parsed = parseApiError(err);
    expect(parsed.type).toBe("NOT_FOUND");
    expect(parsed.message).toBe("not found");
  });

  it("returns NETWORK_ERROR when no response", () => {
    const err = Object.assign(new axios.AxiosError("net"), {
      isAxiosError: true,
      response: undefined,
      config: {},
    });
    const parsed = parseApiError(err);
    expect(parsed.type).toBe("NETWORK_ERROR");
  });

  it("handles non-axios errors gracefully", () => {
    const parsed = parseApiError(new Error("boom"));
    expect(parsed.type).toBe("UNKNOWN");
    expect(parsed.message).toBe("boom");
  });
});
