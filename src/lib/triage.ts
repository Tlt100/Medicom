import type { Flow } from './api';

export type Answers = Record<string, string>;

/**
 * Follows the server's question tree using the current answers.
 * Returns the questions answered so far (in order), the next unanswered question (or null when the
 * flow is finished), and the answers restricted to that path, so changing an earlier answer drops
 * any answers that no longer apply.
 */
export function walk(flow: Flow, answers: Answers): { path: string[]; next: string | null; pruned: Answers } {
  const path: string[] = [];
  const pruned: Answers = {};
  let current: string | null = flow.start;
  while (current) {
    const question: Flow['questions'][string] | undefined = flow.questions[current];
    const value: string | undefined = answers[current];
    const option: Flow['questions'][string]['options'][number] | undefined = question?.options.find((o) => o.value === value);
    if (!question || !option) return { path, next: current, pruned };
    path.push(current);
    pruned[current] = option.value;
    current = option.next;
  }
  return { path, next: null, pruned };
}

/** The suggestion for a question only counts if it's a real option for that question. */
export function suggestedValue(flow: Flow, questionId: string, suggestion: Answers): string | undefined {
  const value = suggestion[questionId];
  return flow.questions[questionId]?.options.some((o) => o.value === value) ? value : undefined;
}
