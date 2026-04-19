import { defineCollection, reference, z } from 'astro:content';

const entries = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().min(1).max(200),
    summary: z.string().min(1).max(400),
    receivedAt: z.coerce.date(),
    source: z.object({
      from: z.string().email().optional(),
      subject: z.string().optional(),
      messageId: z.string().optional(),
    }).default({}),
    tags: z.array(z.string()).default([]),
    threads: z.array(reference('threads')).min(1, {
      message: 'every entry must belong to at least one thread (fold in, do not silo)',
    }),
  }),
});

const threads = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().min(1).max(120),
    summary: z.string().min(1).max(600),
    createdAt: z.coerce.date(),
    updatedAt: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    status: z.enum(['active', 'paused', 'done']).default('active'),
    relatedEntries: z.array(reference('entries')).default([]),
    relatedThreads: z.array(reference('threads')).default([]),
  }),
});

export const collections = { entries, threads };
