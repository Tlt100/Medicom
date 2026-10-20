import { useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { formatDate } from '../../core/api/http';
import { Icon } from '../../core/components/Icon';
import { ClaimBlock, More } from '../../core/components/SourceLinks';
import { formatCents, formatDollars, parseDollars } from '../../core/lib/money';
import { useAsync } from '../../core/lib/useAsync';
import { fetchRules, type Rules } from './api';
import { capCents, evaluate, MAX_HOUSEHOLD, type Answer, type Answers, type Coverage, type EligibilityResult, type ProgramResult, type Status } from './eligibility';

const STATUS_LABEL: Record<Status, string> = {
  may_be_eligible: 'May be eligible',
  check: 'Check with the hospital',
  not_by_income: 'Not based on income',
  does_not_apply: 'Doesn’t apply',
};

function Choice<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
}: {
  name: string;
  legend: string;
  options: { value: T; label: string }[];
  value: T | '';
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="mini-fieldset">
      <legend>{legend}</legend>
      <div className="pill-options">
        {options.map((o) => (
          <label key={o.value} className={value === o.value ? 'pill selected' : 'pill'}>
            <input type="radio" name={name} value={o.value} checked={value === o.value} onChange={() => onChange(o.value)} />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

const YES_NO: { value: Answer; label: string }[] = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'unsure', label: 'I’m not sure' },
];

interface Draft {
  resident: Answer | '';
  coverage: Coverage | '';
  njHospital: Answer | '';
  householdSize: string;
  income: string;
}

const EMPTY: Draft = { resident: '', coverage: '', njHospital: '', householdSize: '', income: '' };

function validate(d: Draft): { answers: Answers } | { problem: string } {
  if (!d.resident || !d.coverage || !d.njHospital) return { problem: 'Answer the three questions about where you live, your coverage and the hospital.' };
  const size = Number(d.householdSize);
  if (!/^\d+$/.test(d.householdSize.trim()) || size < 1 || size > MAX_HOUSEHOLD) return { problem: `Enter a household size from 1 to ${MAX_HOUSEHOLD}.` };
  const income = parseDollars(d.income);
  if (income === null) return { problem: 'Enter your household’s yearly income before taxes as a dollar amount, for example 45000.' };
  return { answers: { resident: d.resident, coverage: d.coverage, njHospital: d.njHospital, householdSize: size, incomeCents: income } };
}

function Questions({ initial, onDone }: { initial: Draft; onDone: (d: Draft, a: Answers) => void }) {
  const [d, setD] = useState<Draft>(initial);
  const [problem, setProblem] = useState<string | null>(null);
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((prev) => ({ ...prev, [k]: v }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const result = validate(d);
    if ('problem' in result) {
      setProblem(result.problem);
      return;
    }
    setProblem(null);
    onDone(d, result.answers);
  };

  return (
    <form className="situation uninsured-form" onSubmit={submit} aria-label="Your situation" noValidate>
      <Choice name="resident" legend="Did you live in New Jersey when you got the care?" options={YES_NO} value={d.resident} onChange={(v) => set('resident', v)} />
      <Choice<Coverage>
        name="coverage"
        legend="Did you have health coverage on the date of service?"
        options={[
          { value: 'none', label: 'No coverage' },
          { value: 'partial', label: 'Yes, but it paid only part of the bill' },
          { value: 'full', label: 'Yes, it covered the care' },
          { value: 'unsure', label: 'I’m not sure' },
        ]}
        value={d.coverage}
        onChange={(v) => set('coverage', v)}
      />
      <Choice name="hospital" legend="Was the care at a hospital in New Jersey?" options={YES_NO} value={d.njHospital} onChange={(v) => set('njHospital', v)} />

      <div className="mini-field">
        <label htmlFor="household">People in your household</label>
        <p className="field-help" id="household-hint">
          Count yourself, and your spouse and dependents if you have them.
        </p>
        <input id="household" inputMode="numeric" aria-describedby="household-hint" value={d.householdSize} onChange={(e) => set('householdSize', e.target.value)} />
      </div>
      <div className="mini-field">
        <label htmlFor="income">Household income for the year, before taxes</label>
        <p className="field-help" id="income-hint">
          Gross income from everyone in the household, in dollars.
        </p>
        <input id="income" inputMode="decimal" aria-describedby="income-hint" value={d.income} onChange={(e) => set('income', e.target.value)} />
      </div>

      {problem && (
        <p className="form-error" role="alert">
          {problem}
        </p>
      )}
      <button type="submit" className="btn btn-primary">
        See what I may be eligible for
      </button>
    </form>
  );
}

function ProgramCard({ id, title, result, children }: { id: string; title: string; result: ProgramResult; children?: ReactNode }) {
  const positive = result.status === 'may_be_eligible' || result.status === 'check';
  return (
    <article className={positive ? 'field-card program-card' : 'field-card field-missing program-card'} aria-labelledby={id}>
      <header className="field-head">
        <h3 id={id}>{title}</h3>
        <span className={positive ? 'status status-found' : 'status status-missing'}>{STATUS_LABEL[result.status]}</span>
      </header>
      <p className="program-headline">{result.headline}</p>
      <ul className="program-reasons">
        {result.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      {children}
    </article>
  );
}

function CapCalculator({ rules }: { rules: Rules }) {
  const [charge, setCharge] = useState('');
  const [medicare, setMedicare] = useState('');
  const pct = rules.uninsured_cap.medicare_percent;
  const chargeCents = parseDollars(charge);
  const medicareCents = parseDollars(medicare);
  const cap = medicareCents === null ? null : capCents(medicareCents, pct);

  return (
    <div className="cap-calc">
      <h4>Check a charge against the {pct}% limit</h4>
      <p className="muted">
        Ask the hospital which Medicare rate it used. <span className="badge badge-guidance">Practical suggestion</span>
      </p>
      <More summary="Why not use the Prices page?">
        <p>
          The <Link to="/prices">Prices</Link> page shows Medicare physician fee schedule amounts, which can differ from the hospital rate the
          law refers to.
        </p>
      </More>
      <div className="cap-inputs">
        <div className="mini-field">
          <label htmlFor="cap-charge">The hospital’s charge</label>
          <input id="cap-charge" inputMode="decimal" value={charge} onChange={(e) => setCharge(e.target.value)} />
        </div>
        <div className="mini-field">
          <label htmlFor="cap-medicare">Medicare payment amount</label>
          <input id="cap-medicare" inputMode="decimal" value={medicare} onChange={(e) => setMedicare(e.target.value)} />
        </div>
      </div>
      <div aria-live="polite">
        {cap !== null && medicareCents !== null && (
          <p className="cap-result">
            {pct}% of {formatCents(medicareCents)} is <strong>{formatCents(cap)}</strong>. Under the 2008 law, that may be the most the hospital can
            charge for this service.
            {chargeCents !== null &&
              (chargeCents > cap
                ? ` The charge you entered is ${formatCents(chargeCents - cap)} more than that, which is worth asking the hospital about.`
                : ' The charge you entered is within that amount.')}
          </p>
        )}
      </div>
    </div>
  );
}

function Results({ rules, answers, result, onEdit, onClear }: { rules: Rules; answers: Answers; result: EligibilityResult; onEdit: () => void; onClear: () => void }) {
  const c = rules.claims;
  const claims = (...ids: string[]) => ids.filter((id) => c[id]).map((id) => <ClaimBlock key={id} claim={c[id]!} />);
  const relevant = (r: ProgramResult) => r.status === 'may_be_eligible' || r.status === 'check';
  const capRelevant = relevant(result.uninsuredCap);
  const charityRelevant = relevant(result.charityCare);

  return (
    <section aria-labelledby="uninsured-results" className="results">
      <div className="results-head">
        <div>
          <p className="eyebrow">Your estimate</p>
          <h2 id="uninsured-results">
            About {result.percentOfPoverty}% of the {result.guidelineYear} poverty guideline
          </h2>
          <p className="muted">
            {formatCents(answers.incomeCents)} a year for a household of {answers.householdSize}. The guideline for that household is{' '}
            {formatDollars(result.povertyLineCents)} ({rules.guideline.region}, effective {formatDate(rules.guideline.effective)}).
          </p>
        </div>
        <div className="results-actions">
          <button type="button" className="btn btn-secondary" onClick={onEdit}>
            Change answers
          </button>
          <button type="button" className="btn btn-quiet" onClick={onClear}>
            Clear my answers
          </button>
        </div>
      </div>
      <p className="muted bill-disclaimer">An estimate, not a decision. The hospital decides.</p>
      <More summary="What this estimate means">
        <p>{rules.disclaimer}</p>
      </More>

      <ProgramCard id="program-charity" title="NJ Charity Care" result={result.charityCare}>
        {charityRelevant
          ? claims('charity_care_what', 'charity_care_income', 'charity_care_who', 'charity_care_assets', 'charity_care_medicaid_first', 'charity_care_not_everything')
          : claims('charity_care_who', 'charity_care_income')}
      </ProgramCard>
      <ProgramCard id="program-cap" title="New Jersey’s limit on hospital charges for uninsured patients" result={result.uninsuredCap}>
        {capRelevant ? claims('nj_uninsured_cap', 'nj_uninsured_sliding_scale') : claims('nj_uninsured_cap')}
        {capRelevant && <CapCalculator rules={rules} />}
      </ProgramCard>

      <h3 className="card-heading">Next steps</h3>
      {claims('charity_care_apply', 'charity_care_hotline', 'good_faith_estimate', 'poverty_guidelines_2026')}
      <p>
        Have insurance after all? <Link to="/bill-check">Compare your bill with your EOB</Link>.
      </p>
    </section>
  );
}

export function Uninsured() {
  const [rules, retry] = useAsync(fetchRules);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [done, setDone] = useState<{ answers: Answers; result: EligibilityResult } | null>(null);
  const [formKey, setFormKey] = useState(0);
  const topRef = useRef<HTMLHeadingElement>(null);

  const focusTop = () => {
    window.scrollTo?.(0, 0);
    topRef.current?.focus();
  };

  return (
    <div className="container page">
      <p className="eyebrow">Uninsured · New Jersey</p>
      <h1 ref={topRef} tabIndex={-1}>
        A hospital bill without insurance
      </h1>
      <p className="lede">A few questions to see if NJ Charity Care or the state’s price limit may apply.</p>
      <p className="retention">
        <Icon name="lock" size={16} /> Calculated on your device. Your income isn’t sent or stored.
      </p>

      {rules.status === 'loading' && (
        <p className="loading" role="status">
          <span className="spinner" aria-hidden="true" /> Loading the rules…
        </p>
      )}
      {rules.status === 'error' && (
        <div className="status-card status-error" role="alert">
          <p>
            <strong>The rules couldn’t be loaded.</strong> {rules.message}
          </p>
          <button type="button" className="btn btn-quiet" onClick={retry}>
            <Icon name="refresh" size={16} /> Try again
          </button>
        </div>
      )}
      {rules.status === 'ready' &&
        (done ? (
          <Results
            rules={rules.data}
            answers={done.answers}
            result={done.result}
            onEdit={() => {
              setDone(null);
              focusTop();
            }}
            onClear={() => {
              setDone(null);
              setDraft(EMPTY);
              setFormKey((k) => k + 1);
              focusTop();
            }}
          />
        ) : (
          <Questions
            key={formKey}
            initial={draft}
            onDone={(d, answers) => {
              setDraft(d);
              setDone({ answers, result: evaluate(answers, rules.data) });
              focusTop();
            }}
          />
        ))}
    </div>
  );
}
