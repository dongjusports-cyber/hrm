import { useEffect, useState } from "react";

import { Link } from "react-router-dom";

import { fetchOrgSummary, type OrgSummary } from "../../shared/api";

import { ConfigTabNav } from "./ConfigTabNav";



/** Admin — Tổ chức (5.6). */

export function OrgAdminPage() {

  const [summary, setSummary] = useState<OrgSummary | null>(null);

  const [error, setError] = useState<string | null>(null);



  useEffect(() => {

    void fetchOrgSummary()

      .then(setSummary)

      .catch((e) => setError(e instanceof Error ? e.message : "Không tải tổ chức."));

  }, []);



  return (

    <div className="config-section-page">

      <ConfigTabNav />

      <h1>Tổ chức</h1>

      <p className="field-hint">

        Cây bộ phận 2 cấp · ca mặc định · hiệu lực · số NV đang thuộc (23§23.4).

      </p>

      {error && <p className="banner-warn">{error}</p>}

      {summary && (

        <div className="kpi-cards">

          <article className="kpi-card">

            <p>Bộ phận</p>

            <strong>

              {summary.active_departments}/{summary.departments}

            </strong>

          </article>

          <article className="kpi-card">

            <p>Tổ</p>

            <strong>

              {summary.active_teams}/{summary.teams}

            </strong>

          </article>

          <article className="kpi-card">

            <p>Chức vụ</p>

            <strong>{summary.positions}</strong>

          </article>

          <article className="kpi-card">

            <p>Công việc</p>

            <strong>{summary.jobs}</strong>

          </article>

        </div>

      )}

      <div className="module-toolbar">

        <Link to="/m/config/departments" className="btn-primary">

          Sửa cây bộ phận / tổ

        </Link>

        <Link to="/m/config/catalogs" className="btn-ghost-dark">

          Danh mục chức vụ / công việc

        </Link>

      </div>

    </div>

  );

}

