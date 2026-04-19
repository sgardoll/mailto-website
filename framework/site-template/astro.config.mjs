import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

const siteUrl = process.env.SITE_URL ?? 'https://example.com';
const base = process.env.SITE_BASE ?? '/';

export default defineConfig({
  site: siteUrl,
  base,
  trailingSlash: 'ignore',
  output: 'static',
  integrations: [mdx(), sitemap()],
  build: {
    assets: 'assets',
  },
});
