import { defineCollection, z } from 'astro:content';

// Articles live at src/content/wiki/<lang>/<category>/<slug>.mdx
// Slug is auto-derived from the file path; we re-split it for routing.
const wiki = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    updated: z.coerce.date().optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { wiki };
