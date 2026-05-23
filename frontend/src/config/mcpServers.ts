import { ExtensionConfig } from '../types/extension';

const BASE_DIR = '/Users/cgaur/Desktop/MCP-ui-poc/mcp-apps-base-chatbot';

export interface PresetServer {
  config: ExtensionConfig;
  sampleQueries: string[];
}

export const PRESET_MCP_SERVERS: PresetServer[] = [
  {
    config: {
      type: 'stdio',
      name: 'weather',
      description: 'Live weather data with visual cards',
      cmd: 'python3',
      args: [`${BASE_DIR}/weather-mcp-server/server.py`],
      envs: {},
    },
    sampleQueries: [
      "What's the weather in Tokyo?",
      'Show me a 5-day forecast for London',
      'Search cities named Portland',
    ],
  },
  {
    config: {
      type: 'stdio',
      name: 'product-catalog',
      description: 'Product search, charts & HTML rendering',
      cmd: 'python3',
      args: [`${BASE_DIR}/sample-mcp-server/server.py`],
      envs: {},
    },
    sampleQueries: [
      'Show me shoes',
      'Search for blue electronics',
      'Show the quarterly sales chart',
      'Display monthly user growth',
    ],
  },
  {
    config: {
      type: 'stdio',
      name: 'text-editor',
      description: 'Interactive text editor with AI refinement',
      cmd: 'python3',
      args: [`${BASE_DIR}/text-editor-mcp-server/server.py`],
      envs: {},
    },
    sampleQueries: [
      'Open a text editor',
      'Open the editor with a paragraph about climate change',
      'Write a short email about a project update',
    ],
  },
];
