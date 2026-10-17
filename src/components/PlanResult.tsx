import { SOURCE_TYPE_LABEL, type SourceRef, type TriageResult } from '../lib/api';
import { Icon } from './Icon';

function SourceLink({ source }: { source: SourceRef }) {
  const binding = source.source_type === 'regulation' || source.source_type === 'statute';
  return (
    <li className="source-ref">
      <span className={binding ? 'badge badge-binding' : 'badge badge-guidance'}>{SOURCE_TYPE_LABEL[source.source_type]}</span>
      {source.verification === 'needs-review' && <span className="badge badge-review">Flagged for review</span>}
      <a href={source.url} target="_blank" rel="noopener noreferrer">
        {source.citation ?? source.title}
        <Icon name="external" size={13} />
        <span className="visually-hidden"> (opens the official source in a new tab)</span>
      </a>
      <span className="source-authority">{source.authority}</span>
    </li>
  );
}

interface Props {
  result: TriageResult;
  onChangeAnswers: () => void;
  onBackToLetter: () => void;
}

export function PlanResult({ result, onChangeAnswers, onBackToLetter }: Props) {
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
              <li key={c.id} className={c.needs_review ? 'claim claim-review' : 'claim'}>
                <p>{c.text}</p>
                <ul className="source-refs" aria-label="Sources">
                  {c.sources.map((s) => (
                    <SourceLink key={s.id} source={s} />
                  ))}
                </ul>
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

      <div className="next-step">
        <h3>Next: your cited checklist</h3>
        <p className="muted">
          The next milestone puts your letter and these rules side by side: an ordered checklist with deadlines, documents to gather,
          questions to ask, and where to escalate.
        </p>
      </div>

      <p className="disclaimer">
        PatientShield is an educational tool, not legal advice. It can’t predict or guarantee the outcome of an appeal. For urgent care,
        contact your plan now and ask for an expedited appeal.
      </p>
    </section>
  );
}
