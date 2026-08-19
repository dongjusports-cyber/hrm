/** Nhận giọng nói tiếng Việt trên điện thoại/Chrome — không tự ghi CSDL. */

export type SpeechSession = { stop: () => void };

type SpeechCtor = new () => {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((ev: SpeechResultEvent) => void) | null;
  onerror: ((ev: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

type SpeechResultEvent = {
  resultIndex?: number;
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
};

export function isSecureSpeechContext(
  win: { isSecureContext?: boolean } | undefined = typeof window !== "undefined" ? window : undefined,
): boolean {
  return Boolean(win?.isSecureContext);
}

export function getSpeechRecognitionCtor(
  win: unknown = typeof window !== "undefined" ? window : undefined,
): SpeechCtor | null {
  if (!win || typeof win !== "object") return null;
  const rec = win as { SpeechRecognition?: SpeechCtor; webkitSpeechRecognition?: SpeechCtor };
  return rec.SpeechRecognition ?? rec.webkitSpeechRecognition ?? null;
}

export function speechBlockReason(
  win: { isSecureContext?: boolean } | undefined = typeof window !== "undefined" ? window : undefined,
): string | null {
  if (!isSecureSpeechContext(win)) {
    return "Giọng nói cần HTTPS. Mở https://hrm.dongju-v.com trên điện thoại (không dùng HTTP LAN).";
  }
  if (!getSpeechRecognitionCtor(win)) {
    return "Trình duyệt không hỗ trợ nói. Dùng Chrome hoặc Edge trên Android, hoặc Safari iOS mới.";
  }
  return null;
}

/** Bỏ «trợ lý ơi / hỏi AI» đầu câu để khớp rule CSDL. */
export function normalizeVoiceCommand(raw: string): string {
  let text = (raw || "").trim().replace(/\s+/g, " ");
  text = text.replace(/^(?:ơ+\s*)?(?:trợ lý(?:\s+ai)?(?:\s+ơi)?|hỏi ai|alo)[\s,.:;]+/i, "");
  text = text.replace(/[.?!,…]+$/g, "").trim();
  return text;
}

function labelSpeechError(code: string): string {
  switch (code) {
    case "not-allowed":
      return "Điện thoại chưa cho phép micro. Bấm Cho phép rồi nói lại.";
    case "no-speech":
      return "Không nghe được. Bấm mic và nói gần máy hơn.";
    case "audio-capture":
      return "Không mở được micro trên máy này.";
    case "network":
      return "Nhận giọng cần mạng (Chrome gửi tiếng nói để nhận chữ). Kiểm tra 4G/WiFi.";
    case "aborted":
      return "";
    default:
      return "Không nhận được giọng nói. Thử Chrome trên Android hoặc gõ chữ.";
  }
}

export function startSpeechSession(opts: {
  lang?: string;
  onInterim?: (text: string) => void;
  onFinal: (text: string) => void;
  onError: (message: string) => void;
  onEnd?: () => void;
  ctor?: SpeechCtor | null;
}): SpeechSession {
  const Ctor = opts.ctor === undefined ? getSpeechRecognitionCtor() : opts.ctor;
  if (!Ctor) {
    opts.onError(speechBlockReason() || "Trình duyệt không hỗ trợ nói.");
    opts.onEnd?.();
    return { stop: () => undefined };
  }

  const rec = new Ctor();
  rec.lang = opts.lang ?? "vi-VN";
  rec.continuous = false;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  let stopped = false;
  let deliveredFinal = false;

  rec.onresult = (ev) => {
    let interim = "";
    let finals = "";
    const start = ev.resultIndex ?? 0;
    for (let i = start; i < ev.results.length; i += 1) {
      const row = ev.results[i];
      const piece = row[0]?.transcript ?? "";
      if (row.isFinal) finals += piece;
      else interim += piece;
    }
    if (interim.trim()) opts.onInterim?.(interim.trim());
    const cleaned = normalizeVoiceCommand(finals);
    if (cleaned && !deliveredFinal) {
      deliveredFinal = true;
      opts.onFinal(cleaned);
    }
  };

  rec.onerror = (ev) => {
    const msg = labelSpeechError(String(ev.error || ""));
    if (msg) opts.onError(msg);
  };

  rec.onend = () => {
    if (!stopped) opts.onEnd?.();
  };

  try {
    rec.start();
  } catch {
    opts.onError("Không bắt đầu nghe được. Bấm mic một lần rồi nói.");
    opts.onEnd?.();
  }

  return {
    stop: () => {
      stopped = true;
      try {
        rec.abort();
      } catch {
        try {
          rec.stop();
        } catch {
          /* ignore */
        }
      }
    },
  };
}
