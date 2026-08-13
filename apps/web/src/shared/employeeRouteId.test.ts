import { describe, expect, it } from "vitest";
import { isEmployeeRouteUuid } from "./employeeRouteId";

describe("isEmployeeRouteUuid", () => {
  it("accepts canonical employee UUID", () => {
    expect(isEmployeeRouteUuid("4f50cc8c-d1b3-40ef-a7a6-9ede4426a119")).toBe(true);
  });

  it("rejects MSNV numeric code", () => {
    expect(isEmployeeRouteUuid("5290")).toBe(false);
  });

  it("rejects partial uuid", () => {
    expect(isEmployeeRouteUuid("4f50cc8c-d1b3")).toBe(false);
  });
});
