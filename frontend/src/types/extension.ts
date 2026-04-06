export interface StdioExtensionConfig {
  type: 'stdio';
  name: string;
  description: string;
  cmd: string;
  args: string[];
  envs: Record<string, string>;
}

export interface HttpExtensionConfig {
  type: 'streamable_http';
  name: string;
  description: string;
  uri: string;
}

export type ExtensionConfig = StdioExtensionConfig | HttpExtensionConfig;

export interface ToolInfo {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
  extension_name: string;
}
