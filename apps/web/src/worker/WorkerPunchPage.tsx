import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { fetchWorkerMe } from "./workerApi";
import { useWorkerAuth } from "./workerAuthStore";
import { WorkerFacePunchButton } from "./WorkerFacePunchButton";

export function WorkerPunchPage() {
  const { worker } = useWorkerAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    void fetchWorkerMe()
      .catch(() => null)
      .finally(() => setReady(true));
  }, []);

  if (ready && worker && worker.can_mobile_punch === false) {
    return <Navigate to="/worker" replace />;
  }

  return (
    <div className="worker-page">
      <header className="worker-top">
        <div>
          <p className="worker-hello">Chấm công</p>
          <h1>{worker?.full_name}</h1>
          <p className="worker-msnv">MSNV {worker?.employee_code}</p>
        </div>
        <Link to="/worker" className="worker-btn-secondary">
          Về trang chủ
        </Link>
      </header>
      <div className="worker-nav">
        <WorkerFacePunchButton />
      </div>
    </div>
  );
}
