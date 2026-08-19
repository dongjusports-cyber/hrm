// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearActiveFieldEsc,
  isEditableFormField,
  registerActiveFieldEsc,
  setFormFieldValue,
  tryRevertActiveFieldEsc,
} from "./formFieldEsc";
import {
  escStackDepth,
  isGridCellEditing,
  registerEscHandler,
  runEscStack,
  setEscFallback,
} from "./escStack";

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

  it("blurs unchanged field without closing overlay", () => {
    const input = document.createElement("input");
    input.type = "text";
    input.value = "hello";
    document.body.appendChild(input);
    input.focus();
    registerActiveFieldEsc(input);

    expect(tryRevertActiveFieldEsc()).toBe(true);
    expect(input.value).toBe("hello");
    expect(document.activeElement).not.toBe(input);

    document.body.removeChild(input);
    clearActiveFieldEsc();
  });

  it("does not swallow Escape when field is on a hidden keep-alive pane", () => {
    const pane = document.createElement("div");
    pane.className = "keep-alive-pane";
    pane.setAttribute("aria-hidden", "true");
    const input = document.createElement("input");
    input.type = "text";
    input.value = "8851";
    pane.appendChild(input);
    document.body.appendChild(pane);
    input.focus();
    registerActiveFieldEsc(input);

    expect(tryRevertActiveFieldEsc()).toBe(false);
    expect(document.activeElement).not.toBe(input);

    document.body.removeChild(pane);
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

  it("does not close overlay when focused field is unchanged", () => {
    const input = document.createElement("input");
    input.type = "text";
    input.value = "x";
    document.body.appendChild(input);
    input.focus();
    registerActiveFieldEsc(input);

    const overlay = vi.fn();
    const unreg = registerEscHandler(overlay);
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(overlay).not.toHaveBeenCalled();
    expect(document.activeElement).not.toBe(input);

    unreg();
    document.body.removeChild(input);
    clearActiveFieldEsc();
  });

  it("runs overlay handler when not editing field or grid", () => {
    const overlay = vi.fn();
    const unreg = registerEscHandler(overlay);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(overlay).toHaveBeenCalledTimes(1);
    unreg();
  });

  it("overlay closes before lower stack layers", () => {
    const lower = vi.fn();
    const top = vi.fn();
    const unregLower = registerEscHandler(lower);
    const unregTop = registerEscHandler(top);

    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(top).toHaveBeenCalledTimes(1);
    expect(lower).not.toHaveBeenCalled();

    unregTop();
    unregLower();
  });

  it("no-op overlay falls through to page-back fallback", () => {
    const fallback = vi.fn();
    setEscFallback(fallback);
    const unreg = registerEscHandler(() => false);
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
    expect(fallback).toHaveBeenCalledTimes(1);
    unreg();
  });

  it("Escape on hidden keep-alive search field falls through to page back", () => {
    const pane = document.createElement("div");
    pane.className = "keep-alive-pane";
    pane.setAttribute("aria-hidden", "true");
    const input = document.createElement("input");
    input.type = "text";
    input.value = "8851";
    pane.appendChild(input);
    document.body.appendChild(pane);
    input.focus();
    registerActiveFieldEsc(input);

    const fallback = vi.fn();
    setEscFallback(fallback);
    const unreg = registerEscHandler(() => false);
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));

    expect(fallback).toHaveBeenCalledTimes(1);
    expect(document.activeElement).not.toBe(input);

    unreg();
    document.body.removeChild(pane);
    clearActiveFieldEsc();
  });

  it("runEscStack skips false layers then hits fallback", () => {
    const fallback = vi.fn();
    const lower = vi.fn(() => false as const);
    setEscFallback(fallback);
    const unregLower = registerEscHandler(lower);
    const unregTop = registerEscHandler(() => false);
    expect(runEscStack()).toBe(true);
    expect(lower).toHaveBeenCalledTimes(1);
    expect(fallback).toHaveBeenCalledTimes(1);
    unregTop();
    unregLower();
  });

  it("detects ag grid editing container", () => {
    const el = document.createElement("div");
    el.className = "ag-cell-inline-editing";
    expect(isGridCellEditing(el)).toBe(true);
  });
});
