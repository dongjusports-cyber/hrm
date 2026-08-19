import { describe, expect, it } from "vitest";
import { workerLoginGate } from "./workerLoginGate";

describe("workerLoginGate", () => {
  it("leftover token must confirm identity, never silent enter", () => {
    expect(workerLoginGate("jwt-from-previous-worker")).toBe("confirm-session");
  });

  it("empty session shows the credential form", () => {
    expect(workerLoginGate(null)).toBe("credentials");
    expect(workerLoginGate("")).toBe("credentials");
    expect(workerLoginGate(undefined)).toBe("credentials");
  });
});
