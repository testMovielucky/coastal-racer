declare const __BUILD__: { version: string; revision: string; builtAt: string };

interface Window {
  coastalCoastPreview?: { snapshot: () => import('./app/coastPreview').CoastPreviewReport };
  coastalCarPreview?: { snapshot: () => import('./app/carPreview').CarPreviewReport };
  coastalDiagnostics?: { snapshot: () => import('./app/stand').StandReport };
}
