/** Cache RAM + IndexedDB trên máy HR — tăng tốc lưới, không thay dữ liệu VPS. */

const DB_NAME = "djhrm-ui-cache";
const STORE = "kv";
const DB_VERSION = 1;
const FRESH_MS = 45_000;

type Entry<T> = { at: number; data: T };

const ram = new Map<string, Entry<unknown>>();

export function cachePeek<T>(key: string): T | undefined {
  const hit = ram.get(key);
  return hit ? (hit.data as T) : undefined;
}

export function cacheSet<T>(key: string, data: T): void {
  ram.set(key, { at: Date.now(), data });
  void idbPut(key, data);
}

export function cacheInvalidate(prefix: string): void {
  for (const key of [...ram.keys()]) {
    if (key === prefix || key.startsWith(prefix)) ram.delete(key);
  }
  void idbDeletePrefix(prefix);
}

/** Cập nhật 1 phần tử trong list đã cache. Không tạo cache 1 dòng (tránh GET sau đó tưởng đủ cả nhà máy). */
export function cacheUpsertListItem<T>(
  key: string,
  item: T,
  match: (existing: T) => boolean,
): void {
  const current = cachePeek<T[]>(key);
  if (!Array.isArray(current)) return;
  const idx = current.findIndex(match);
  const next =
    idx >= 0 ? current.map((row, i) => (i === idx ? item : row)) : [...current, item];
  cacheSet(key, next);
}

export function cacheClearAll(): void {
  ram.clear();
  void idbClear();
}

export function employeesCacheKey(filters: {
  q?: string;
  status?: string;
  department_id?: string;
  team_id?: string;
} = {}): string {
  return `employees:${filters.status ?? ""}|${filters.department_id ?? ""}|${filters.team_id ?? ""}|${filters.q ?? ""}`;
}

export async function cachedFetch<T>(key: string, loader: () => Promise<T>): Promise<T> {
  const hit = ram.get(key) as Entry<T> | undefined;
  if (hit && Date.now() - hit.at < FRESH_MS) return hit.data;
  const data = await loader();
  cacheSet(key, data);
  return data;
}

export async function cacheHydrate<T>(key: string): Promise<T | undefined> {
  const ramHit = cachePeek<T>(key);
  if (ramHit !== undefined) return ramHit;
  const disk = await idbGet<T>(key);
  if (disk !== undefined) ram.set(key, { at: 0, data: disk });
  return disk;
}

function openDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === "undefined") return Promise.resolve(null);
  return new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE);
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => resolve(null);
    } catch {
      resolve(null);
    }
  });
}

async function idbGet<T>(key: string): Promise<T | undefined> {
  const db = await openDb();
  if (!db) return undefined;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(key);
      req.onsuccess = () => resolve(req.result as T | undefined);
      req.onerror = () => resolve(undefined);
    } catch {
      resolve(undefined);
    }
  });
}

async function idbPut(key: string, data: unknown): Promise<void> {
  const db = await openDb();
  if (!db) return;
  try {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(data, key);
  } catch {
    /* ổ đầy / private mode — bỏ qua */
  }
}

async function idbDeletePrefix(prefix: string): Promise<void> {
  const db = await openDb();
  if (!db) return;
  try {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    const req = store.getAllKeys();
    req.onsuccess = () => {
      for (const k of req.result) {
        const key = String(k);
        if (key === prefix || key.startsWith(prefix)) store.delete(k);
      }
    };
  } catch {
    /* ignore */
  }
}

async function idbClear(): Promise<void> {
  const db = await openDb();
  if (!db) return;
  try {
    db.transaction(STORE, "readwrite").objectStore(STORE).clear();
  } catch {
    /* ignore */
  }
}
