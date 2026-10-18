/**
 * The workflows offered from "What did you receive?". `ready` is the only source of truth for whether a path can be used;
 * a path that isn't ready links to an explanation page and never to an upload.
 */
export type PathId = 'denial' | 'bill-check' | 'uninsured';

export interface EntryPath {
  id: PathId;
  route: string;
  title: string;
  description: string;
  ready: boolean;
}

export const ENTRY_PATHS: readonly EntryPath[] = [
  {
    id: 'denial',
    route: '/navigator',
    title: 'A denial letter',
    description: 'Your insurer refused to cover or pay for care. See what the letter says, which rules apply, and your next steps.',
    ready: true,
  },
  {
    id: 'bill-check',
    route: '/bill-check',
    title: 'A bill, and I have insurance',
    description: 'Compare a provider’s bill with your insurer’s Explanation of Benefits (EOB) and see which lines are worth asking about.',
    ready: false,
  },
  {
    id: 'uninsured',
    route: '/uninsured',
    title: 'A bill, and I don’t have insurance',
    description: 'For New Jersey hospital bills: see whether you may be eligible for limits on what uninsured patients can be charged.',
    ready: false,
  },
];

export function entryPath(id: PathId): EntryPath {
  const path = ENTRY_PATHS.find((p) => p.id === id);
  if (!path) throw new Error(`Unknown path: ${id}`);
  return path;
}
