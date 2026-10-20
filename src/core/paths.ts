import type { IconName } from './components/Icon';

/** The workflows offered from "What did you receive?", and the main navigation. */
export type PathId = 'denial' | 'bill-check' | 'uninsured';

export interface EntryPath {
  id: PathId;
  route: string;
  title: string;
  description: string;
  /** Short name for the navigation bar. */
  navLabel: string;
  icon: IconName;
}

export const ENTRY_PATHS: readonly EntryPath[] = [
  {
    id: 'denial',
    route: '/navigator',
    title: 'A denial letter',
    description: 'See what it says and how to appeal.',
    navLabel: 'Denial letter',
    icon: 'doc',
  },
  {
    id: 'bill-check',
    route: '/bill-check',
    title: 'A bill, with insurance',
    description: 'Check it against your insurer’s statement (EOB).',
    navLabel: 'Bill check',
    icon: 'checklist',
  },
  {
    id: 'uninsured',
    route: '/uninsured',
    title: 'A bill, no insurance',
    description: 'See if NJ Charity Care or price limits may apply.',
    navLabel: 'No insurance',
    icon: 'scale',
  },
];
