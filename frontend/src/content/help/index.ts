/**
 * Help System Content Registry
 *
 * Central registry for all help articles with types, search indexing, and utilities.
 */

import React from 'react';

// Help categories for organizing content
export type HelpCategory =
  | 'getting-started'
  | 'scenarios'
  | 'traffic-generation'
  | 'device-management'
  | 'security-testing'
  | 'administration'
  | 'reference';

// Category metadata for display
export const categoryInfo: Record<HelpCategory, { label: string; icon: string; order: number }> = {
  'getting-started': { label: 'Getting Started', icon: 'RocketOutlined', order: 1 },
  'scenarios': { label: 'Scenarios', icon: 'FolderOutlined', order: 2 },
  'traffic-generation': { label: 'Traffic Generation', icon: 'CloudServerOutlined', order: 3 },
  'device-management': { label: 'Device Management', icon: 'DatabaseOutlined', order: 4 },
  'security-testing': { label: 'Security Testing', icon: 'SafetyOutlined', order: 5 },
  'administration': { label: 'Administration', icon: 'SettingOutlined', order: 6 },
  'reference': { label: 'Reference', icon: 'BookOutlined', order: 7 },
};

// Help article structure
export interface HelpArticle {
  id: string;                    // URL slug (e.g., "scenario-studio")
  title: string;                 // Display title
  category: HelpCategory;        // Category for grouping
  keywords: string[];            // For search indexing
  summary: string;               // Brief description for search results
  content: React.FC;             // JSX content component
  relatedArticles?: string[];    // Related article IDs
  relatedPages?: string[];       // Related route paths (e.g., "/studio")
  order: number;                 // Sort order within category
}

// Search result with relevance scoring
export interface HelpSearchResult {
  article: HelpArticle;
  matchedKeywords: string[];
  relevanceScore: number;
}

// Content registry - populated by article imports
const helpArticles: Map<string, HelpArticle> = new Map();

/**
 * Register a help article in the registry
 */
export function registerHelpArticle(article: HelpArticle): void {
  helpArticles.set(article.id, article);
}

/**
 * Get all registered help articles
 */
export function getAllArticles(): HelpArticle[] {
  return Array.from(helpArticles.values()).sort((a, b) => {
    const catOrderA = categoryInfo[a.category].order;
    const catOrderB = categoryInfo[b.category].order;
    if (catOrderA !== catOrderB) return catOrderA - catOrderB;
    return a.order - b.order;
  });
}

/**
 * Get articles grouped by category
 */
export function getArticlesByCategory(): Map<HelpCategory, HelpArticle[]> {
  const grouped = new Map<HelpCategory, HelpArticle[]>();

  for (const article of getAllArticles()) {
    const existing = grouped.get(article.category) || [];
    grouped.set(article.category, [...existing, article]);
  }

  return grouped;
}

/**
 * Get a single article by ID
 */
export function getArticle(id: string): HelpArticle | undefined {
  return helpArticles.get(id);
}

/**
 * Get articles for a specific category
 */
export function getArticlesForCategory(category: HelpCategory): HelpArticle[] {
  return getAllArticles().filter(a => a.category === category);
}

/**
 * Search articles by query string
 * Returns results sorted by relevance
 */
export function searchArticles(query: string): HelpSearchResult[] {
  if (!query.trim()) return [];

  const normalizedQuery = query.toLowerCase().trim();
  const queryTerms = normalizedQuery.split(/\s+/);
  const results: HelpSearchResult[] = [];

  for (const article of getAllArticles()) {
    let score = 0;
    const matchedKeywords: string[] = [];

    // Title match (highest weight)
    const titleLower = article.title.toLowerCase();
    for (const term of queryTerms) {
      if (titleLower.includes(term)) {
        score += 10;
        matchedKeywords.push(`title: ${term}`);
      }
    }

    // Exact title match bonus
    if (titleLower === normalizedQuery) {
      score += 20;
    }

    // Summary match (medium weight)
    const summaryLower = article.summary.toLowerCase();
    for (const term of queryTerms) {
      if (summaryLower.includes(term)) {
        score += 5;
        matchedKeywords.push(`summary: ${term}`);
      }
    }

    // Keyword match (medium weight)
    for (const keyword of article.keywords) {
      const keywordLower = keyword.toLowerCase();
      for (const term of queryTerms) {
        if (keywordLower.includes(term) || term.includes(keywordLower)) {
          score += 3;
          matchedKeywords.push(keyword);
        }
      }
    }

    // Category match (low weight)
    if (categoryInfo[article.category].label.toLowerCase().includes(normalizedQuery)) {
      score += 2;
    }

    if (score > 0) {
      results.push({
        article,
        matchedKeywords: [...new Set(matchedKeywords)],
        relevanceScore: score,
      });
    }
  }

  return results.sort((a, b) => b.relevanceScore - a.relevanceScore);
}

/**
 * Get related articles for a given article
 */
export function getRelatedArticles(articleId: string): HelpArticle[] {
  const article = getArticle(articleId);
  if (!article) return [];

  const related: HelpArticle[] = [];

  // Add explicitly related articles
  if (article.relatedArticles) {
    for (const relatedId of article.relatedArticles) {
      const relatedArticle = getArticle(relatedId);
      if (relatedArticle) related.push(relatedArticle);
    }
  }

  // Add other articles from same category (up to 3)
  const sameCategory = getArticlesForCategory(article.category)
    .filter(a => a.id !== articleId && !related.some(r => r.id === a.id))
    .slice(0, 3);

  return [...related, ...sameCategory].slice(0, 5);
}

/**
 * Find article relevant to a given route path
 */
export function getArticleForRoute(route: string): HelpArticle | undefined {
  for (const article of getAllArticles()) {
    if (article.relatedPages?.includes(route)) {
      return article;
    }
  }
  return undefined;
}

// Import and register all articles
// These will be populated as content files are created
import { gettingStartedArticle } from './getting-started';
import { scenariosArticle } from './scenarios';
import { scenarioStudioArticle } from './scenario-studio';
import { deviceLibraryArticle } from './device-library';

import { deploymentsArticle } from './deployments';
import { ipManagementArticle } from './ip-management';
import { cveBrowserArticle } from './cve-browser';
import { adminSettingsArticle } from './admin-settings';
import { templatesArticle } from './templates';
import { anomaliesArticle } from './anomalies';
import { glossaryArticle } from './glossary';
import { dockerHostSetupArticle } from './docker-host-setup';

// Register all articles
registerHelpArticle(gettingStartedArticle);
registerHelpArticle(scenariosArticle);
registerHelpArticle(scenarioStudioArticle);
registerHelpArticle(deviceLibraryArticle);

registerHelpArticle(deploymentsArticle);
registerHelpArticle(ipManagementArticle);
registerHelpArticle(cveBrowserArticle);
registerHelpArticle(adminSettingsArticle);
registerHelpArticle(templatesArticle);
registerHelpArticle(anomaliesArticle);
registerHelpArticle(glossaryArticle);
registerHelpArticle(dockerHostSetupArticle);
