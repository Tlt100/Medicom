import { Link } from 'react-router-dom';
import { Icon, type IconName } from '../components/Icon';
import { fetchRegistry, formatDate } from '../lib/api';
import { useAsync } from '../lib/useAsync';

/** Research figures for context. Verified on 2026-10-17 against the KFF analysis linked below. */
const KFF_URL = 'https://www.kff.org/patient-consumer-protections/claims-denials-and-appeals-in-aca-marketplace-plans-in-2024/';
const STATS = [
  { value: '19%', label: 'of in-network claims were denied by HealthCare.gov marketplace insurers in 2024' },
  { value: '<1%', label: 'of those denied claims were appealed by consumers' },
];

const STEPS: { icon: IconName; title: string; body: string }[] = [
  {
    icon: 'upload',
    title: 'Add your denial letter',
    body: 'Upload a PDF or text file. It is read in memory to find the details and is not stored.',
  },
  {
    icon: 'route',
    title: 'Identify your plan type',
    body: 'A few questions determine which rules apply. Plan type changes your appeal path, so we ask before advising.',
  },
  {
    icon: 'checklist',
    title: 'Get a cited checklist',
    body: 'Ordered next steps, documents to gather, questions to ask, and the right official contacts, each tied to a source.',
  },
];

const PLAN_TYPES = [
  'NJ state-regulated (fully insured)',
  'Self-funded employer plan (ERISA)',
  'ACA marketplace (Get Covered New Jersey)',
  'NJ FamilyCare / Medicaid',
  'Medicare / Medicare Advantage',
  'Not sure yet',
];

function SourceStatus() {
  const [state, retry] = useAsync(fetchRegistry);

  if (state.status === 'loading') {
    return (
      <div className="status-card" aria-busy="true" aria-live="polite">
        <span className="skeleton skeleton-line" />
        <span className="skeleton skeleton-line short" />
        <span className="visually-hidden">Loading source library status…</span>
      </div>
    );
  }
  if (state.status === 'error') {
    return (
      <div className="status-card status-error" role="alert">
        <p>
          <strong>Source library status is unavailable.</strong> {state.message}
        </p>
        <button type="button" className="btn btn-quiet" onClick={retry}>
          <Icon name="refresh" size={16} /> Try again
        </button>
      </div>
    );
  }

  const { coverage, last_reviewed } = state.data;
  return (
    <div className="status-card" aria-live="polite">
      <dl className="status-grid">
        <div>
          <dt>Official sources</dt>
          <dd>{coverage.total}</dd>
        </div>
        <div>
          <dt>Verified against the source</dt>
          <dd>{coverage.verified}</dd>
        </div>
        <div>
          <dt>Flagged for human review</dt>
          <dd>{coverage.needs_review}</dd>
        </div>
        <div>
          <dt>Binding regulations</dt>
          <dd>{coverage.binding}</dd>
        </div>
      </dl>
      <p className="status-foot">
        {coverage.federal} federal · {coverage.nj} New Jersey · Library last reviewed {formatDate(last_reviewed)}
      </p>
    </div>
  );
}

export function Landing() {
  return (
    <>
      <section className="hero">
        <div className="container hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">New Jersey · U.S. federal law</p>
            <h1>Understand your insurance denial, line by line.</h1>
            <p className="lede">
              PatientShield reads a denial letter, shows exactly where each detail appears, and explains which New Jersey or federal rules
              apply to your type of plan, with a source for every claim.
            </p>
            <div className="hero-actions">
              <Link to="/navigator" className="btn btn-primary">
                Open the Denial Navigator <Icon name="arrow" size={18} />
              </Link>
              <Link to="/sources" className="btn btn-secondary">
                Browse verified sources
              </Link>
            </div>
            <p className="hero-note">
              <Icon name="lock" size={16} /> No account. Letters are processed in memory and not stored.
            </p>
          </div>

          <figure className="preview" aria-labelledby="preview-caption">
            <div className="preview-col">
              <p className="preview-label">
                <Icon name="doc" size={16} /> Your letter says
              </p>
              <blockquote className="preview-quote">
                “You may request an appeal within 180 days of the date you receive this notice.”
              </blockquote>
              <p className="preview-meta">Page 1 · highlighted in your document</p>
            </div>
            <div className="preview-col preview-col-law">
              <p className="preview-label">
                <Icon name="scale" size={16} /> The rules say
              </p>
              <p className="preview-claim">Private employer health plans must give you at least 180 days after a denial to file an appeal.</p>
              <p className="preview-cite">
                <span className="badge badge-binding">Regulation</span> 29 CFR § 2560.503-1(h)(3)(i)
              </p>
            </div>
            <figcaption id="preview-caption" className="preview-caption">
              Illustration using a synthetic letter. The two columns are always kept separate.
            </figcaption>
          </figure>
        </div>
      </section>

      <section className="section band" aria-labelledby="why-heading">
        <div className="container">
          <h2 id="why-heading" className="visually-hidden">
            Why this matters
          </h2>
          <div className="stats">
            {STATS.map((s) => (
              <div className="stat" key={s.value}>
                <p className="stat-value">{s.value}</p>
                <p className="stat-label">{s.label}</p>
              </div>
            ))}
            <p className="stat-context">
              The barrier is usually not a missing appeal letter. It is not knowing what a denial means or which rules apply.{' '}
              <span className="stat-source">
                Source:{' '}
                <a href={KFF_URL} target="_blank" rel="noopener noreferrer">
                  KFF, Claims Denials and Appeals in ACA Marketplace Plans in 2024 (March 2026)
                  <Icon name="external" size={14} />
                </a>
                . Covers HealthCare.gov plans only; New Jersey’s state-run marketplace is not included.
              </span>
            </p>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="how-heading">
        <div className="container">
          <p className="eyebrow">How it works</p>
          <h2 id="how-heading">From a confusing letter to a clear next step</h2>
          <ol className="steps">
            {STEPS.map((s, i) => (
              <li className="step" key={s.title}>
                <span className="step-icon">
                  <Icon name={s.icon} size={22} />
                </span>
                <span className="step-num">Step {i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section section-tint" aria-labelledby="principles-heading">
        <div className="container split">
          <div>
            <p className="eyebrow">Built on sources</p>
            <h2 id="principles-heading">What the document says is never mixed with what the law says</h2>
            <ul className="principles">
              <li>
                <strong>Quoted, not guessed.</strong> Every detail pulled from your letter links to its page and passage. If something
                isn’t there, we say so.
              </li>
              <li>
                <strong>Plan type first.</strong> New Jersey’s external appeal program doesn’t cover self-funded plans or Medicare, so we
                confirm your plan type before giving plan-specific steps.
              </li>
              <li>
                <strong>Uncertainty is labelled.</strong> Sources we couldn’t fully verify are flagged for review and never shown as fact.
              </li>
            </ul>
          </div>
          <div>
            <h3 className="card-heading">Source library status</h3>
            <SourceStatus />
            <h3 className="card-heading">Plan types the navigator distinguishes</h3>
            <ul className="chip-list">
              {PLAN_TYPES.map((p) => (
                <li key={p} className="chip">
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="limits-heading">
        <div className="container">
          <div className="callout">
            <Icon name="alert" size={22} className="callout-icon" />
            <div>
              <h2 id="limits-heading" className="callout-title">
                Know the limits
              </h2>
              <p>
                PatientShield is an educational tool, not legal advice, and it can’t predict or guarantee an appeal outcome. If your care is
                urgent, contact your insurer now and ask for an expedited (urgent) appeal. For emergencies, call 911.
              </p>
              <Link to="/about" className="text-link">
                Read the full scope and limitations <Icon name="arrow" size={16} />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
