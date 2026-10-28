import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: './openapi.json',
  output: {
    path: './src/generated',
    clean: true,
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/typescript',
    {
      name: '@hey-api/sdk',
      operations: {
        // The backend names operations "<Tag>.<handler>"; group them as <Tag>Controller.<handler>().
        strategy: (operation) => {
          const [tag, method] = operation.operationId!.split('.');
          return [[`${tag}Controller`, method]];
        },
        methods: 'static',
      },
    },
  ],
});
