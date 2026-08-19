import { Link } from "react-router-dom";
import type { ReactNode } from "react";

export type ModuleLayer = {
  label: string;
  to?: string;
  current?: boolean;
};

/**
 * Thanh tầng Portal — nút dài nổi, mỗi tầng 1 nút (giống Nhân Sự).
 */
export function ModuleLayerHeader({
  layers,
  right,
}: {
  layers: ModuleLayer[];
  right?: ReactNode;
}) {
  return (
    <header className="module-header hr-layer-header">
      <nav className="hr-layer-left" aria-label="Tầng trang">
        {layers.map((layer) =>
          layer.to && !layer.current ? (
            <Link key={layer.label} to={layer.to} className="hr-layer-btn">
              {layer.label}
            </Link>
          ) : (
            <span key={layer.label} className="hr-layer-btn is-current">
              {layer.label}
            </span>
          ),
        )}
      </nav>
      {right ? <div className="hr-layer-right">{right}</div> : null}
    </header>
  );
}
