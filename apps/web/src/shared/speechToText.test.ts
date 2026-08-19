import { describe, expect, it, vi } from "vitest";
import {
  getSpeechRecognitionCtor,
  isSecureSpeechContext,
  normalizeVoiceCommand,
  speechBlockReason,
  startSpeechSession,
} from "./speechToText";

describe("normalizeVoiceCommand", () => {
  it("bỏ trợ lý ơi / hỏi AI đầu câu", () => {
    expect(normalizeVoiceCommand("Trợ lý ơi ai chấm lẻ tháng này")).toBe("ai chấm lẻ tháng này");
    expect(normalizeVoiceCommand("hỏi AI tóm tắt việc cần làm hôm nay")).toBe(
      "tóm tắt việc cần làm hôm nay",
    );
    expect(normalizeVoiceCommand("Tóm tắt việc cần làm hôm nay.")).toBe(
      "Tóm tắt việc cần làm hôm nay",
    );
  });
});

describe("speech capability", () => {
  it("HTTPS mới được coi an toàn", () => {
    expect(isSecureSpeechContext({ isSecureContext: true })).toBe(true);
    expect(isSecureSpeechContext({ isSecureContext: false })).toBe(false);
  });

  it("không có SpeechRecognition → null", () => {
    expect(getSpeechRecognitionCtor({})).toBeNull();
  });

  it("HTTP → hướng dẫn mở VPS HTTPS", () => {
    const reason = speechBlockReason({ isSecureContext: false });
    expect(reason).toContain("HTTPS");
    expect(reason).toContain("hrm.dongju-v.com");
  });
});

describe("startSpeechSession", () => {
  it("không ctor → onError, không ném", () => {
    const onError = vi.fn();
    const onFinal = vi.fn();
    const session = startSpeechSession({ ctor: null, onFinal, onError });
    expect(onError).toHaveBeenCalled();
    expect(onFinal).not.toHaveBeenCalled();
    session.stop();
  });

  it("kết quả isFinal → normalize rồi onFinal", () => {
    class FakeRec {
      lang = "";
      continuous = false;
      interimResults = false;
      maxAlternatives = 1;
      onresult: ((ev: {
        results: Array<{ isFinal: boolean; 0: { transcript: string } }>;
      }) => void) | null = null;
      onerror: ((ev: { error?: string }) => void) | null = null;
      onend: (() => void) | null = null;
      start() {
        this.onresult?.({
          results: [{ isFinal: true, 0: { transcript: "Trợ lý ơi đơn phép chờ duyệt" } }],
        });
        this.onend?.();
      }
      stop() {}
      abort() {}
    }
    const onFinal = vi.fn();
    const onError = vi.fn();
    startSpeechSession({
      ctor: FakeRec as unknown as new () => FakeRec,
      onFinal,
      onError,
    });
    expect(onFinal).toHaveBeenCalledWith("đơn phép chờ duyệt");
    expect(onError).not.toHaveBeenCalled();
  });
});
