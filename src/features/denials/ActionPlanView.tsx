import { formatDate } from '../../core/api/http';
import { type ActionPlan } from './api';
import { Icon } from '../../core/components/Icon';
import { ClaimBlock, SourceLink } from '../../core/components/SourceLinks';

const STEP_KIND: Record<ActionPlan['steps'][number]['kind'], string> = {
  urgent: 'Urgent',
  rule: 'Based on the rules',
  letter: 'From your letter',
  practical: 'Practical step',
};

function Quote({ text, page }: { text: string; page: number }) {
  return (
    <blockquote className="letter-quote">
      “{text}”<cite>Your letter, page {page}</cite>
    </blockquote>
  );
}

interface Props {
  plan: ActionPlan;
  onEditSituation: () => void;
  onBackToLetter: () => void;
}

export function ActionPlanView({ plan, onEditSituation, onBackToLetter }: Props) {
  return (
    <section aria-labelledby="action-heading" className="action-plan">
      <div className="results-head">
        <div>
          <p className="eyebrow">Step 4 · Your action plan</p>
          <h2 id="action-heading">Your action plan</h2>
          <p className="muted">
            {plan.label} · Prepared {formatDate(plan.today)}
          </p>
        </div>
        <div className="head-actions no-print">
          <button type="button" className="btn btn-secondary" onClick={() => window.print()}>
            Print or save as PDF
          </button>
          <button type="button" className="btn btn-quiet" onClick={onEditSituation}>
            Edit details
          </button>
          <button type="button" className="btn btn-quiet" onClick={onBackToLetter}>
            Back to your letter
          </button>
        </div>
      </div>

      {plan.plan_around && (
        <p className="plan-around" role="status">
          <Icon name="alert" size={20} /> {plan.plan_around}
        </p>
      )}

      <section aria-labelledby="deadlines-heading" className="plan-section">
        <h3 id="deadlines-heading">Deadlines</h3>
        {plan.deadlines.length === 0 ? (
          <p className="muted">
            No calendar deadlines yet. Add the date you received the letter, or confirm your plan type, to see dates.
          </p>
        ) : (
          <ol className="deadline-list">
            {plan.deadlines.map((d) => (
              <li key={d.id} className={d.passed ? 'deadline passed' : 'deadline'}>
                <div className="deadline-date">
                  <span className="deadline-day">{formatDate(d.date)}</span>
                  <span className="deadline-left">{d.passed ? `${-d.days_left} days ago` : `${d.days_left} days left`}</span>
                </div>
                <div className="deadline-body">
                  <p className="deadline-label">
                    <span className={d.kind === 'letter' ? 'badge badge-letter' : 'badge badge-binding'}>
                      {d.kind === 'letter' ? 'Stated in your letter' : 'General rule'}
                    </span>{' '}
                    {d.label}
                  </p>
                  <p className="deadline-basis">{d.basis}</p>
                  {d.note && <p className="field-note">{d.note}</p>}
                  {d.quote && <Quote text={d.quote.text} page={d.quote.page} />}
                  {d.claim && (
                    <ul className="source-refs" aria-label="Sources">
                      {d.claim.sources.map((s) => (
                        <SourceLink key={s.id} source={s} />
                      ))}
                    </ul>
                  )}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section aria-labelledby="compare-heading" className="plan-section">
        <h3 id="compare-heading">Your letter and the rules, side by side</h3>
        <div className="compare">
          <div className="compare-head" aria-hidden="true">
            <span>What your letter says</span>
            <span>What the rules say</span>
          </div>
          {plan.comparisons.map((row) => (
            <article key={row.topic} className="compare-row" aria-label={row.topic}>
              <h4>{row.topic}</h4>
              <div className="compare-cols">
                <div className="compare-letter">
                  <p className="compare-label">What your letter says</p>
                  <p className={row.letter_status === 'found' ? 'compare-summary' : 'compare-summary missing'}>{row.letter_summary}</p>
                  {row.letter && <Quote text={row.letter.text} page={row.letter.page} />}
                </div>
                <div className="compare-rules">
                  <p className="compare-label">What the rules say</p>
                  {row.rules.map((c) => (
                    <ClaimBlock key={c.id} claim={c} />
                  ))}
                  {row.rules_summary && <p className="compare-summary muted">{row.rules_summary}</p>}
                </div>
              </div>
              {row.note && (
                <p className="compare-note">
                  <Icon name="scale" size={16} /> {row.note}
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section aria-labelledby="steps-heading" className="plan-section">
        <h3 id="steps-heading">Checklist</h3>
        <ol className="checklist">
          {plan.steps.map((s) => (
            <li key={s.id} className={`check-step step-${s.kind}`}>
              <div className="check-head">
                <h4>{s.title}</h4>
                <span className="badge badge-kind">{STEP_KIND[s.kind]}</span>
              </div>
              {s.due && <p className="check-due">By {formatDate(s.due)}</p>}
              <p>{s.detail}</p>
              {s.quote && <Quote text={s.quote.text} page={s.quote.page} />}
              {s.claims.map((c) => (
                <ClaimBlock key={c.id} claim={c} />
              ))}
            </li>
          ))}
        </ol>
      </section>

      <div className="plan-lists">
        <section aria-labelledby="docs-heading" className="side-card">
          <h3 id="docs-heading" className="card-heading">
            Documents to gather
          </h3>
          <ul>
            {plan.documents.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="questions-heading" className="side-card">
          <h3 id="questions-heading" className="card-heading">
            Questions to ask the plan
          </h3>
          <ul>
            {plan.questions.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </section>
      </div>

      {plan.contacts.length > 0 && (
        <section aria-labelledby="contacts-heading" className="plan-section">
          <h3 id="contacts-heading">Where to get help</h3>
          <ul className="contacts">
            {plan.contacts.map((c) => (
              <li key={c.name} className="contact">
                <p className="contact-name">{c.name}</p>
                <p className="muted">{c.when}</p>
                {c.phone && <p className="contact-phone">{c.phone}</p>}
                <ul className="source-refs" aria-label="Source">
                  <SourceLink source={c.source} />
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}

      {plan.uncertainties.length > 0 && (
        <section aria-labelledby="unsure-heading" className="side-card side-card-warn plan-section">
          <h3 id="unsure-heading" className="card-heading">
            What we couldn’t confirm
          </h3>
          <ul>
            {plan.uncertainties.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </section>
      )}

      <p className="disclaimer">{plan.disclaimer}</p>
    </section>
  );
}
