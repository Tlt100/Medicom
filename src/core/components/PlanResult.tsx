import type { ReactNode } from 'react';
import type { TriageResult } from '../api/triage';
import { Icon } from './Icon';
import { ClaimBlock } from './SourceLinks';

interface Props {
  result: TriageResult;
  onChangeAnswers: () => void;
  onBackToLetter: () => void;
  /** Rendered where the next step goes (the situation form that builds the action plan). */
  children?: ReactNode;
}

export function PlanResult({ result, onChangeAnswers, onBackToLetter, children }: Props) {
  const confirmed = result.confidence === 'confirmed';
  return (
    <section aria-labelledby="plan-heading" className="plan-result">
      <div className="results-head">
        <div>
          <p className="eyebrow">Step 3 · What applies to your plan</p>
          <h2 id="plan-heading">{result.label}</h2>
          <p className={confirmed ? 'confidence confirmed' : 'confidence unconfirmed'}>
            <Icon name={confirmed ? 'checklist' : 'alert'} size={16} />
            {confirmed ? 'Based on your answers' : 'Needs confirmation: some answers were “not sure”'}
          </p>
        </div>
        <div className="head-actions">
          <button type="button" className="btn btn-secondary" onClick={onChangeAnswers}>
            Change answers
          </button>
          <button type="button" className="btn btn-quiet" onClick={onBackToLetter}>
            Back to your letter
          </button>
        </div>
      </div>

      <p className="plan-summary">{result.summary}</p>

      <div className="plan-grid">
        <div>
          <h3 className="card-heading">What the rules say for this plan type</h3>
          <ol className="claims">
            {result.claims.map((c) => (
              <li key={c.id}>
                <ClaimBlock claim={c} />
              </li>
            ))}
          </ol>
        </div>

        <aside className="plan-side">
          {result.regulator && (
            <div className="side-card">
              <h3 className="card-heading">Who oversees this plan type</h3>
              <p className="regulator">{result.regulator.name}</p>
              {result.regulator.source && (
                <a href={result.regulator.source.url} target="_blank" rel="noopener noreferrer" className="text-link">
                  {result.regulator.source.title} <Icon name="external" size={13} />
                  <span className="visually-hidden"> (opens in a new tab)</span>
                </a>
              )}
            </div>
          )}

          {result.uncertainties.length > 0 && (
            <div className="side-card side-card-warn">
              <h3 className="card-heading">What we couldn’t confirm</h3>
              <ul>
                {result.uncertainties.map((u) => (
                  <li key={u}>{u}</li>
                ))}
              </ul>
            </div>
          )}

          <details className="side-card" open={result.plan_type === 'unknown' || !confirmed}>
            <summary>How to confirm your plan type</summary>
            <ol>
              {result.how_to_confirm.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ol>
          </details>

          <div className="side-card">
            <h3 className="card-heading">Your answers</h3>
            <dl className="answers">
              {result.answers.map((a) => (
                <div key={a.question}>
                  <dt>{a.question}</dt>
                  <dd>{a.answer}</dd>
                </div>
              ))}
            </dl>
          </div>
        </aside>
      </div>

      {children}

      <p className="disclaimer">
        PatientShield is an educational tool, not legal advice. It can’t predict or guarantee the outcome of an appeal. For urgent care,
        contact your plan now and ask for an expedited appeal.
      </p>
    </section>
  );
}
