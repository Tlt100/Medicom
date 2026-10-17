import { useEffect, useRef, useState } from 'react';
import { fetchFlow, fetchSuggestion, runTriage, type Flow, type Suggestion, type TriageResult } from '../lib/api';
import { suggestedValue, walk, type Answers } from '../lib/triage';
import { useAsync } from '../lib/useAsync';
import { Icon } from './Icon';

interface Props {
  signals: string[];
  initialAnswers?: Answers;
  onBack: () => void;
  onDone: (result: TriageResult, answers: Answers) => void;
}

const loadFlow = (signal: AbortSignal) => fetchFlow(signal);

/** The questions on the current path, plus the next unanswered one. */
function sequence(flow: Flow, answers: Answers): string[] {
  const { path, next } = walk(flow, answers);
  return next ? [...path, next] : path;
}

function Questions({ flow, signals, initialAnswers, onBack, onDone }: Props & { flow: Flow }) {
  const [answers, setAnswers] = useState<Answers>(() => walk(flow, initialAnswers ?? {}).pruned);
  const [index, setIndex] = useState(0);
  const [suggestion, setSuggestion] = useState<Suggestion>({ answers: {}, reasons: [] });
  const [choice, setChoice] = useState<{ question: string; value: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const legendRef = useRef<HTMLLegendElement>(null);
  const moved = useRef(false);

  const seq = sequence(flow, answers);
  const current = seq[Math.min(index, seq.length - 1)]!;
  const question = flow.questions[current]!;
  const suggested = suggestedValue(flow, current, suggestion.answers);
  // The radio shows: what the user picked on this screen, else their earlier answer, else the letter's suggestion.
  const selected = choice?.question === current ? choice.value : (answers[current] ?? suggested ?? '');

  useEffect(() => {
    if (!signals.length) return;
    const ctrl = new AbortController();
    fetchSuggestion(signals, ctrl.signal)
      .then(setSuggestion)
      .catch(() => {
        /* suggestions are optional; the questions work without them */
      });
    return () => ctrl.abort();
  }, [signals]);

  useEffect(() => {
    if (moved.current) legendRef.current?.focus();
  }, [current]);

  const goBack = () => {
    setError(null);
    if (index === 0) return onBack();
    moved.current = true;
    setIndex(index - 1);
  };

  const onContinue = async () => {
    if (!selected) return;
    const updated = walk(flow, { ...answers, [current]: selected }).pruned;
    setAnswers(updated);
    setChoice(null);
    const option = question.options.find((o) => o.value === selected);
    if (option?.next) {
      moved.current = true;
      setIndex(index + 1);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      onDone(await runTriage(updated), updated);
    } catch (err) {
      setError((err as Error).message);
      setSubmitting(false);
    }
  };

  const showSuggestion = suggested !== undefined && answers[current] === undefined && selected === suggested;
  const helpId = `help-${question.id}`;

  return (
    <form
      className="triage"
      onSubmit={(e) => {
        e.preventDefault();
        void onContinue();
      }}
    >
      <p className="triage-progress">Question {index + 1}</p>
      <fieldset aria-describedby={helpId}>
        <legend ref={legendRef} tabIndex={-1}>
          {question.prompt}
        </legend>
        <p className="muted" id={helpId}>
          {question.help}
        </p>
        {showSuggestion && (
          <p className="suggestion" role="note">
            <Icon name="doc" size={16} />
            <span>
              Pre-selected from your letter: {suggestion.reasons.join(' ')} Check that it’s right before continuing.
            </span>
          </p>
        )}
        <div className="options">
          {question.options.map((o) => (
            <label key={o.value} className={selected === o.value ? 'option selected' : 'option'}>
              <input
                type="radio"
                name={question.id}
                value={o.value}
                checked={selected === o.value}
                onChange={() => setChoice({ question: current, value: o.value })}
              />
              <span>
                <span className="option-label">{o.label}</span>
                {o.hint && <span className="option-hint">{o.hint}</span>}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}

      <div className="triage-actions">
        <button type="button" className="btn btn-secondary" onClick={goBack} disabled={submitting}>
          Back
        </button>
        <button type="submit" className="btn btn-primary" disabled={!selected || submitting}>
          {submitting ? 'Checking…' : 'Continue'} <Icon name="arrow" size={18} />
        </button>
      </div>
    </form>
  );
}

export function Triage(props: Props) {
  const [state, retry] = useAsync(loadFlow);
  if (state.status === 'loading') {
    return (
      <p className="loading" role="status">
        <span className="spinner" aria-hidden="true" /> Loading questions…
      </p>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="status-card status-error" role="alert">
        <p>
          <strong>The questions couldn’t load.</strong> {state.message}
        </p>
        <button type="button" className="btn btn-quiet" onClick={retry}>
          <Icon name="refresh" size={16} /> Try again
        </button>
      </div>
    );
  }
  return <Questions {...props} flow={state.data} />;
}
