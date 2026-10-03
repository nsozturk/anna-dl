import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
  site: 'https://nsozturk.github.io',
  base: '/anna-dl',
  integrations: [
    starlight({
      title: 'anna-dl',
      description: 'Resilient, Zero-Key Shadow Library Downloader CLI & AI Agent',
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/nsozturk/anna-dl' },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Introduction', slug: 'index' },
            { label: 'Installation', slug: 'getting-started/installation' },
            { label: 'Quick Start', slug: 'getting-started/quickstart' },
          ],
        },
        {
          label: 'CLI Reference',
          items: [
            { label: 'Commands & Flags', slug: 'cli/commands' },
            { label: 'Batch & Parallel Worker', slug: 'cli/batch' },
            { label: 'DNS Bypass', slug: 'cli/dns-bypass' },
          ],
        },
        {
          label: 'AI Agents & Automation',
          items: [
            { label: 'Claude Code & AI Agents', slug: 'agents/claude-code' },
            { label: 'Global Agent Rule', slug: 'agents/global-rule' },
          ],
        },
        {
          label: 'Architecture & Evasion',
          items: [
            { label: 'DDoS-Guard JS Challenge Solver', slug: 'architecture/ddos-guard' },
            { label: '10-Candidate MD5 Recovery Loop', slug: 'architecture/md5-loop' },
            { label: '2026 Mirror Network', slug: 'architecture/mirrors' },
          ],
        },
      ],
    }),
  ],
});
