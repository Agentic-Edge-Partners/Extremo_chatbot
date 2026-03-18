export interface AppConfig {
  name: string;
  description: string;
}

export const APP_CONFIG: AppConfig = {
  name: process.env.NEXT_PUBLIC_APP_NAME ?? "Extremo Ambiente",
  description:
    process.env.NEXT_PUBLIC_APP_DESCRIPTION ??
    "AI-powered corporate event planner",
};
