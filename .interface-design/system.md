# Interface design system

## Direction

Operational reports should feel like focused work surfaces: familiar, compact, and easy to scan. Reuse the app's Bootstrap/AdminLTE components and existing theme rather than introducing a separate visual language.

## Foundations

- **Palette:** Use the existing Bootstrap/AdminLTE theme colors for primary actions, neutral controls, and report surfaces. Do not introduce decorative colors or new hex values in report filters.
- **Depth:** Keep the existing card and border treatment; avoid adding custom shadows or extra surface layers to report controls.
- **Spacing:** Use the Bootstrap 4px spacing scale and existing grid gutters (`g-3` where supported by the project).
- **Typography:** Inherit the app's existing font, label, and heading styles.

## Report filters

- Place filters directly above the charts and report data they affect.
- Use labeled, full-width Bootstrap form controls in the existing responsive grid.
- Keep date, branch, and seller selections visible after submitting; preserve them in print and pagination links.
- Apply each selected filter consistently to table rows, totals, and charts.
- Scope branch choices to the user's warehouse access and seller choices to their company.
