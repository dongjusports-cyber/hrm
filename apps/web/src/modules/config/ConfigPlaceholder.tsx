import { Link, useParams } from "react-router-dom";
import { CONFIG_SECTIONS } from "./configSections";

export function ConfigPlaceholder() {
  const { sectionKey = "" } = useParams();
  const section = CONFIG_SECTIONS.find((s) => s.key === sectionKey);

  return (
    <div>
      <h1>{section?.name ?? sectionKey}</h1>
      <p className="module-placeholder">
        Mục này sẽ được dựng ở phiên tiếp theo theo Hiến pháp (P1.2+).
      </p>
      <Link to="/m/config" className="hr-layer-btn">
        ← Cấu Hình
      </Link>
    </div>
  );
}
