declare const __BUILD__: { version: string; revision: string; builtAt: string };

interface Window {
  coastalDiagnostics?: { snapshot: () => import('./app/stand').StandReport };
}
