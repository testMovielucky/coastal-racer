declare const __BUILD__: { version: string; revision: string; builtAt: string };

interface Window {
  coastalCarPreview?: { snapshot: () => import('./app/carPreview').CarPreviewReport };
  coastalDiagnostics?: { snapshot: () => import('./app/stand').StandReport };
}
