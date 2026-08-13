import {
  fetchIntegrationStatus,
  fetchSyncJobs,
  requestSyncNow,
  type SyncJob,
} from "../../shared/api";
import { labelJobStatus } from "../../shared/viLabels";

export type SyncProgressState = {
  active: boolean;
  percent: number;
  message: string;
  ok: boolean | null;
};

const TERMINAL = new Set(["success", "partial", "error"]);

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function estimatePercent(status: string, elapsedMs: number, queueAhead: number): number {
  if (status === "success" || status === "partial") return 100;
  if (status === "error") return 100;
  if (status === "running") return Math.min(92, 48 + Math.floor(elapsedMs / 2000));
  if (status === "requested") {
    const base = 10 + Math.min(28, queueAhead * 6);
    return Math.min(45, base + Math.floor(elapsedMs / 4000));
  }
  return 8;
}

function resultMessage(job: SyncJob): { ok: boolean; message: string } {
  if (job.status === "success") {
    return {
      ok: true,
      message: `Đồng bộ thành công — thêm ${job.records_inserted} lần chấm, bỏ trùng ${job.records_skipped}.`,
    };
  }
  if (job.status === "partial") {
    return {
      ok: true,
      message: job.message || "Đồng bộ xong một phần — kiểm tra nhật ký.",
    };
  }
  return {
    ok: false,
    message: job.message || "Đồng bộ thất bại — kiểm tra máy Agent tại nhà máy.",
  };
}

async function findJob(jobId: string): Promise<SyncJob | null> {
  const { items } = await fetchSyncJobs(15);
  return items.find((j) => j.id === jobId) ?? null;
}

function queueAheadCount(items: SyncJob[], jobId: string, jobStartedAt: string | null): number {
  if (!jobStartedAt) return 0;
  const mine = new Date(jobStartedAt).getTime();
  return items.filter((j) => {
    if (j.status !== "requested" || j.id === jobId || !j.started_at) return false;
    return new Date(j.started_at).getTime() < mine;
  }).length;
}

function progressMessage(
  status: string,
  queueAhead: number,
  anyRunning: boolean,
): string {
  if (anyRunning) {
    return "Agent đang đồng bộ dữ liệu Mitapro…";
  }
  if (status === "requested" && queueAhead > 0) {
    return `Đang chờ Agent (${queueAhead} yêu cầu trước bạn). Agent poll mỗi ~15 phút — giữ cửa sổ mở.`;
  }
  if (status === "requested") {
    return "Đang chờ máy nhà máy nhận lệnh… (Agent poll mỗi ~15 phút)";
  }
  if (status === "running") {
    return "Máy đồng bộ đang tải chấm công…";
  }
  return `Trạng thái: ${labelJobStatus(status)}…`;
}

/** Yêu cầu đồng bộ và chờ kết quả — báo % tiến độ cho HR. */
export async function runSyncWithProgress(
  onProgress: (state: SyncProgressState) => void,
  options?: {
    timeoutMs?: number;
    createJob?: () => Promise<SyncJob>;
  },
): Promise<{ ok: boolean; message: string }> {
  const timeoutMs = options?.timeoutMs ?? 600_000;
  const createJob = options?.createJob ?? requestSyncNow;
  const started = Date.now();

  onProgress({ active: true, percent: 5, message: "Đang gửi yêu cầu đồng bộ…", ok: null });

  const requested = await createJob();
  const jobId = requested.id;

  while (Date.now() - started < timeoutMs) {
    const [{ items }, st] = await Promise.all([fetchSyncJobs(20), fetchIntegrationStatus()]);
    const job = (await findJob(jobId)) ?? items.find((j) => j.id === jobId) ?? requested;
    const status = job.status;
    const queueAhead = queueAheadCount(items, jobId, job.started_at);
    const anyRunning = items.some((j) => j.status === "running");
    const percent = estimatePercent(status, Date.now() - started, queueAhead);
    const message = progressMessage(status, queueAhead, anyRunning);

    if (TERMINAL.has(status)) {
      const result = resultMessage(job);
      onProgress({ active: true, percent: 100, message: result.message, ok: result.ok });
      return result;
    }

    onProgress({ active: true, percent, message, ok: null });

    const last = st.last_job;
    if (last && last.id === jobId && TERMINAL.has(last.status)) {
      const result = resultMessage(last);
      onProgress({ active: true, percent: 100, message: result.message, ok: result.ok });
      return result;
    }

    await sleep(2500);
  }

  const fail =
    "Hết thời gian chờ (10 phút) — Agent chưa xử lý xong. Kiểm tra Agent trên máy Mitapro đang chạy và SYNC_INTERVAL_MINUTES (nên ≤2 khi test).";
  onProgress({ active: true, percent: 100, message: fail, ok: false });
  return { ok: false, message: fail };
}
