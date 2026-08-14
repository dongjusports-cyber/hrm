// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearActiveFieldEsc,
  isEditableFormField,
  registerActiveFieldEsc,
  setFormFieldValue,
  tryRevertActiveFieldEsc,
} from "./formFieldEsc";
import { escStackDepth, isGridCellEditing, registerEscHandler, setEscFallback } from "./escStack";

describe("isEditableFormField", () => {
  it("accepts text input", () => {
    const input = document.createElement("input");
    input.type = "text";
    expect(isEditableFormField(input)).toBe(true);
  });

  it("rejects checkbox", () => {
    const input = document.createElement("input");
    input.type = "checkbox";
    expect(isEditableFormField(input)).toBe(false);
  });
});

describe("tryRevertActiveFieldEsc", () => {
  it("reverts focused input to snapshot value", () => {
    const input = document.createElement("input");
    input.type = "text";
    input.value = "hello";
    document.body.appendChild(input);
    input.focus();
    registerActiveFieldEsc(input);
    input.value = "changed";

    expect(tryRevertActiveFieldEsc()).toBe(true);
    expect(input.value).toBe("hello");
    expect(document.activeElement).not.toBe(input);

    document.body.removeChild(input);
    clearActiveFieldEsc();
  });

  it("returns false when nothing registered", () => {
    clearActiveFieldEsc();
    expect(tryRevertActiveFieldEsc()).toBe(false);
  });

  it("calls onRevert callback", () => {
    const input = document.createElement("input");
    input.type = "text";
    input.value = "a";
    document.body.appendChild(input);
    input.focus();
    const onRevert = vi.fn();
    registerActiveFieldEsc(input, onRevert);
    input.value = "b";

    expect(tryRevertActiveFieldEsc()).toBe(true);
    expect(onRevert).toHaveBeenCalledTimes(1);

    document.body.removeChild(input);
    clearActiveFieldEsc();
  });
});

describe("setFormFieldValue", () => {
  it("fires input event for React controlled fields", () => {
    const input = document.createElement("input");
    const spy = vi.fn();
    input.addEventListener("input", spy);
    setFormFieldValue(input, "x");
    expect(input.value).toBe("x");
    expect(spy).toHaveBeenCalled();
  });
});

describe("escStack priority", () => {
  beforeEach(() => {
    setEscFallback(null);
    while (escStackDepth() > 0) {
      /* drained by unregister in afterEach */
    }
  });

  afterEach(() => {
    setEscFallback(null);
  });

  it("reverts Escape in AG Grid cell editor before overlay", () => {
    const grid = document.createElement("div");
    grid.className = "ag-theme-quartz";
    const cell = document.createElement("div");
    cell.className = "ag-cell-inline-editing";
    const input = document.createElement("input");
    input.type = "text";
    input.value = "07:30";
    cell.appendChild(input);
    grid.appendChild(cell);
    document.body.appendChild(grid);
    input.focus();
    registerActiveFieldEsc(input);
    input.value = "08:00";

    const overlay = vi.fn();
    const unreg = registerEscHandler(overlay);

    const prevented = { value: false };
    const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
    event.preventDefault = () => {
      prevented.value = true;
    };
    window.dispatchEvent(event);

    expect(prevented.value).toBe(true);
    expect(input.value).toBe("07:30");
    expect(overlay).not.toHaveBeenCalled();

    unreg();
    document.body.removeChild(grid);
    clearActiveFieldEsc();
  });

  it("runs overlay handler when not editing field or grid", () => {
    const overlay = vi.fn();
    const unreg = registerEscHandler(overlay);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(overlay).toHaveBeenCalledTimes(1);
    unreg();
  });

  it("detects ag grid editing container", () => {
    const el = document.createElement("div");
    el.className = "ag-cell-inline-editing";
    expect(isGridCellEditing(el)).toBe(true);
  });
});
