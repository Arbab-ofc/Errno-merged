import { existsSync, readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

describe('Admin document shell', () => {
  it('references a bundled favicon asset', () => {
    const html = readFileSync('index.html', 'utf8');
    expect(html).toContain('href="/favicon.svg"');
    expect(existsSync('public/favicon.svg')).toBe(true);
  });
});
