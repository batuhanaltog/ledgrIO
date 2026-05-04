import { renderHook, act } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { useOpenClose, useEditModal, useDeleteConfirm } from "./useModalState";

describe("useOpenClose", () => {
  it("starts closed", () => {
    const { result } = renderHook(() => useOpenClose());
    expect(result.current.isOpen).toBe(false);
  });
  it("opens and closes", () => {
    const { result } = renderHook(() => useOpenClose());
    act(() => result.current.open());
    expect(result.current.isOpen).toBe(true);
    act(() => result.current.close());
    expect(result.current.isOpen).toBe(false);
  });
});

describe("useEditModal", () => {
  it("starts null", () => {
    const { result } = renderHook(() => useEditModal<{ id: number }>());
    expect(result.current.selected).toBeNull();
  });
  it("opens with item and closes", () => {
    const { result } = renderHook(() => useEditModal<{ id: number }>());
    act(() => result.current.open({ id: 42 }));
    expect(result.current.selected).toEqual({ id: 42 });
    act(() => result.current.close());
    expect(result.current.selected).toBeNull();
  });
});

describe("useDeleteConfirm", () => {
  it("starts null", () => {
    const { result } = renderHook(() => useDeleteConfirm());
    expect(result.current.pendingId).toBeNull();
  });
  it("sets and clears pendingId", () => {
    const { result } = renderHook(() => useDeleteConfirm());
    act(() => result.current.confirm(7));
    expect(result.current.pendingId).toBe(7);
    act(() => result.current.cancel());
    expect(result.current.pendingId).toBeNull();
  });
});
