import type {NextConfig} from 'next';
const config:NextConfig={basePath:process.env.NEXT_PUBLIC_REGISTRY_BASE_PATH||''};
export default config;
