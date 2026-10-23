import { expect, test } from "@playwright/test";

test("persists real dashboard filters and exposes a deterministic empty state", async ({
  page,
  request,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Resumen General" })).toBeVisible();
  await expect(page.getByText(/2019-2025/).first()).toBeVisible();
  await expect(page.getByText("Producción").last()).toBeVisible();

  const department = page.getByRole("combobox", { name: "Departamento", exact: true });
  await expect.poll(() => department.locator("option").count()).toBeGreaterThan(1);
  const departmentCode = "05";
  await expect(department.locator(`option[value="${departmentCode}"]`)).toHaveText(
    "Antioquia",
  );
  await department.selectOption(departmentCode);
  await expect(page).toHaveURL(new RegExp(`department=${departmentCode}`));

  const crop = page.getByRole("combobox", { name: "Cultivo", exact: true });
  await expect.poll(() => crop.locator("option").count()).toBeGreaterThan(1);
  const papaOption = crop.locator("option").filter({ hasText: /^Papa$/ });
  const cropId = await papaOption.getAttribute("value");
  expect(cropId).toMatch(/^\d+$/);
  await crop.selectOption(cropId!);
  await expect(page).toHaveURL(new RegExp(`crop=${cropId}`));

  const summaryResponse = await request.get("http://localhost:8000/api/v1/agriculture/summary", {
    params: {
      year_from: 2025,
      year_to: 2025,
      period_mode: "AGRICULTURAL_YEAR",
      indicator: "production_t",
      department: departmentCode,
      crop: cropId!,
    },
  });
  expect(summaryResponse.ok()).toBe(true);
  const summary = await summaryResponse.json();
  const expectedProduction = `${new Intl.NumberFormat("es-CO", {
    maximumFractionDigits: 2,
  }).format(Number(summary.data.production_t))} t`;
  const productionValue = page
    .locator(".kpi-card")
    .filter({ hasText: "Producción" })
    .locator("strong");
  await expect(productionValue).toHaveText(expectedProduction);
  const valuesBeforeReload = await page.locator(".kpi-card strong").allTextContents();

  await page.reload();
  await expect(department).toHaveValue(departmentCode);
  await expect(crop).toHaveValue(cropId!);
  const kpis = page.getByRole("region", { name: "Indicadores principales" });
  await expect(kpis.getByText("Producción", { exact: true })).toBeVisible();
  await expect(productionValue).toHaveText(expectedProduction);
  await expect(page.locator(".kpi-card strong")).toHaveText(valuesBeforeReload);

  const yieldHelp = page.getByRole("button", { name: "Información sobre rendimiento" });
  await yieldHelp.focus();
  await expect(page.getByRole("tooltip")).toContainText("Producción total dividida");

  await page.goto(
    "/?crop=999999&year=2025&period_mode=AGRICULTURAL_YEAR&indicator=production_t",
  );
  await expect(page.getByText("No hay datos para estos filtros")).toBeVisible();
  expect(consoleErrors).toEqual([]);
});
