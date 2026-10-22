import { RotateCcw, SlidersHorizontal } from "lucide-react";

import type { Crop, Department, Municipality } from "@/types/api";
import type { DashboardFilters as DashboardFilterValues } from "@/types/filters";

type FilterSetter = <K extends keyof DashboardFilterValues>(
  key: K,
  value: DashboardFilterValues[K] | undefined,
) => void;

type DashboardFiltersProps = {
  crops: Crop[];
  departments: Department[];
  filters: DashboardFilterValues;
  municipalities: Municipality[];
  onChange: FilterSetter;
  onReset: () => void;
};

export function DashboardFilters({
  crops,
  departments,
  filters,
  municipalities,
  onChange,
  onReset,
}: DashboardFiltersProps) {
  return (
    <section className="filters" aria-label="Filtros del panel">
      <div className="filters__title">
        <SlidersHorizontal size={18} aria-hidden="true" />
        <span>Filtros</span>
      </div>
      <label>
        <span>Departamento</span>
        <select
          value={filters.department ?? ""}
          onChange={(event) => onChange("department", event.target.value || undefined)}
        >
          <option value="">Todo Colombia</option>
          {departments.map((department) => (
            <option value={department.code} key={department.code}>
              {department.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Municipio</span>
        <select
          disabled={!filters.department}
          value={filters.municipality ?? ""}
          onChange={(event) => onChange("municipality", event.target.value || undefined)}
        >
          <option value="">Todos los municipios</option>
          {municipalities.map((municipality) => (
            <option value={municipality.code} key={municipality.code}>
              {municipality.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Cultivo</span>
        <select
          value={filters.crop ?? ""}
          onChange={(event) =>
            onChange("crop", event.target.value ? Number(event.target.value) : undefined)
          }
        >
          <option value="">Todos los cultivos</option>
          {crops.map((crop) => (
            <option value={crop.id} key={crop.id}>
              {crop.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Año</span>
        <select
          value={filters.year}
          onChange={(event) => onChange("year", Number(event.target.value))}
        >
          {Array.from({ length: 7 }, (_, index) => 2025 - index).map((year) => (
            <option value={year} key={year}>
              {year}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span>Lectura temporal</span>
        <select
          value={filters.periodMode}
          onChange={(event) =>
            onChange(
              "periodMode",
              event.target.value as DashboardFilterValues["periodMode"],
            )
          }
        >
          <option value="AGRICULTURAL_YEAR">Año agrícola</option>
          <option value="SOURCE">Periodos de la fuente</option>
        </select>
      </label>
      <label>
        <span>Indicador</span>
        <select
          value={filters.indicator}
          onChange={(event) =>
            onChange(
              "indicator",
              event.target.value as DashboardFilterValues["indicator"],
            )
          }
        >
          <option value="production_t">Producción</option>
          <option value="planted_area_ha">Área sembrada</option>
          <option value="harvested_area_ha">Área cosechada</option>
          <option value="yield_t_ha">Rendimiento</option>
        </select>
      </label>
      <button className="button button--quiet filters__reset" type="button" onClick={onReset}>
        <RotateCcw size={15} aria-hidden="true" />
        Restablecer
      </button>
    </section>
  );
}
