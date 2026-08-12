import { describe, expect, it } from "vitest";
import { digitsOnlyMoney, employeeToForm, formToPayload } from "./employeeFormState";

describe("digitsOnlyMoney", () => {
  it("API decimal → số nguyên VND", () => {
    expect(digitsOnlyMoney("8335000.00")).toBe("8335000");
    expect(digitsOnlyMoney("8335000.0")).toBe("8335000");
  });

  it("giữ số đã format khi gõ/blur", () => {
    expect(digitsOnlyMoney("8,335,000")).toBe("8335000");
    expect(digitsOnlyMoney("8335000")).toBe("8335000");
  });
});

describe("employee 1519 save round-trip", () => {
  const toDateInput = (v: string | null | undefined) => v ?? "";

  it("8335000.00 từ API không bị phình thành 833500000", () => {
    const form = employeeToForm(
      {
        employee_code: "1519",
        full_name: "Nguyễn Benchmark",
        contract_salary: "8335000.00",
        probation_salary: "8335000.00",
      },
      toDateInput,
    );
    const payload = formToPayload(form, false);
    expect(payload.contract_salary).toBe("8335000");
    expect(payload.probation_salary).toBe("8335000");
  });
});
