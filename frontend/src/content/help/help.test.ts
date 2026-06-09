/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Help-content guardrails.
 *
 * The 2026-06 help audit found articles that had silently drifted years behind
 * the app (dead settings tabs, missing pages, 3 of 9 protocols). These tests
 * keep the registry structurally honest:
 *  - every navigable route in App.tsx resolves to a help article
 *  - no two articles claim the same route
 *  - cross-links point at registered articles
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import {
  getAllArticles,
  getArticle,
  getArticleForRoute,
  categoryInfo,
} from './index';

/** Parse user-navigable (non-redirect) route paths out of App.tsx. */
function appRoutes(): string[] {
  // vitest runs with cwd at the frontend package root
  const source = readFileSync(resolve(process.cwd(), 'src/App.tsx'), 'utf-8');

  const routes: string[] = [];
  for (const match of source.matchAll(/path="([^"]+)"/g)) {
    const path = match[1];
    if (path === '*' || path.includes(':')) continue; // catch-all & param routes
    // Redirect routes mention Navigate/Redirect in the same Route tag, so
    // only look as far as the next <Route.
    const start = match.index ?? 0;
    const nextRoute = source.indexOf('<Route', start + 1);
    const tail = source.slice(start, Math.min(start + 250, nextRoute === -1 ? start + 250 : nextRoute));
    if (/Navigate|Redirect/.test(tail)) continue;
    routes.push(path.startsWith('/') ? path : `/${path}`);
  }
  return routes;
}

// Routes that intentionally have no help article mapping.
const EXEMPT_ROUTES = new Set([
  '/login', // pre-auth, no help chrome
  '/help', // the help system itself
]);

describe('help registry', () => {
  it('covers every navigable app route with an article', () => {
    const routes = appRoutes();
    expect(routes.length).toBeGreaterThan(10); // parser sanity check

    const uncovered = routes.filter(
      (route) => !EXEMPT_ROUTES.has(route) && !getArticleForRoute(route),
    );
    expect(uncovered, `routes without a help article: ${uncovered.join(', ')}`).toEqual([]);
  });

  it('has no route claimed by more than one article', () => {
    const seen = new Map<string, string>();
    for (const article of getAllArticles()) {
      for (const page of article.relatedPages ?? []) {
        const owner = seen.get(page);
        expect(owner, `${page} claimed by both ${owner} and ${article.id}`).toBeUndefined();
        seen.set(page, article.id);
      }
    }
  });

  it('only claims routes that exist in App.tsx', () => {
    const routes = new Set(appRoutes());
    for (const article of getAllArticles()) {
      for (const page of article.relatedPages ?? []) {
        const exists =
          routes.has(page) || [...routes].some((r) => r.startsWith(`${page}/`) || page.startsWith(`${r}/`));
        expect(exists, `${article.id} claims dead route ${page}`).toBe(true);
      }
    }
  });

  it('resolves param routes via prefix matching', () => {
    expect(getArticleForRoute('/libraries/attacks/triton_like')?.id).toBe('attack-simulation');
  });

  it('has valid cross-links and categories', () => {
    for (const article of getAllArticles()) {
      expect(categoryInfo[article.category], `${article.id} has unknown category`).toBeDefined();
      for (const relatedId of article.relatedArticles ?? []) {
        expect(getArticle(relatedId), `${article.id} links to missing article ${relatedId}`).toBeDefined();
      }
    }
  });
});
