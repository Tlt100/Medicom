import { useState, type FormEvent } from 'react';
import { formatDate } from '../../core/api/http';
import { type Situation } from './api';
import { Icon } from '../../core/components/Icon';

interface Props {
  letterDate: string | null;
  initial?: Situation;
  submitting: boolean;
  error: string | null;
  onSubmit: (s: Situation) => void;
}

function Choice<T extends string>({
  name,
  legend,
  value,
  options,
  onChange,
}: {
  name: string;
  legend: string;
  value: T;
  options: [T, string][];
  onChange: (v: T) => void;
}) {
  return (
    <fieldset className="mini-fieldset">
      <legend>{legend}</legend>
      <div className="pill-options">
        {options.map(([v, label]) => (
          <label key={v} className={value === v ? 'pill selected' : 'pill'}>
            <input type="radio" name={name} value={v} checked={value === v} onChange={() => onChange(v)} />
            {label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

// Local calendar date (en-CA formats as YYYY-MM-DD), so the check matches what the user sees.
const today = () => new Date().toLocaleDateString('en-CA');

/** Asks only what the letter can't tell us. Every field is optional except the choices, which default to "not sure". */
export function SituationForm({ letterDate, initial, submitting, error, onSubmit }: Props) {
  const [s, setS] = useState<Situation>(
    initial ?? { date_received: letterDate, care_received: 'unsure', internal_appeal: 'not_yet', final_decision_date: null, urgent: 'unsure' },
  );
  const [problem, setProblem] = useState<string | null>(null);
  const set = <K extends keyof Situation>(k: K, v: Situation[K]) => setS((prev) => ({ ...prev, [k]: v }));

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (s.date_received && s.date_received > today()) return setProblem('The date you received the letter can’t be in the future.');
    if (s.final_decision_date && s.final_decision_date > today()) return setProblem('The decision date can’t be in the future.');
    setProblem(null);
    onSubmit({ ...s, final_decision_date: s.internal_appeal === 'decided' ? s.final_decision_date : null });
  };

  return (
    <form className="situation" onSubmit={submit} aria-labelledby="situation-heading" noValidate>
      <h3 id="situation-heading">Build your action plan</h3>
      <p className="muted">A few details your letter can’t tell us. They’re used for this page only and aren’t saved.</p>

      <div className="situation-grid">
        <div className="mini-field">
          <label htmlFor="date-received">When did you receive the letter?</label>
          <input
            id="date-received"
            type="date"
            max={today()}
            value={s.date_received ?? ''}
            onChange={(e) => set('date_received', e.target.value || null)}
            aria-describedby="date-received-help"
          />
          <p id="date-received-help" className="field-help">
            {letterDate
              ? `Filled in with the date printed on your letter (${formatDate(letterDate)}). Change it if the letter arrived later.`
              : 'Your letter has no date we could find. Deadlines often count from when you received it.'}
          </p>
        </div>

        <Choice
          name="urgent"
          legend="Could waiting seriously harm your health?"
          value={s.urgent}
          options={[
            ['yes', 'Yes'],
            ['no', 'No'],
            ['unsure', 'Not sure'],
          ]}
          onChange={(v) => set('urgent', v)}
        />

        <Choice
          name="care"
          legend="Have you already received the care?"
          value={s.care_received}
          options={[
            ['yes', 'Yes'],
            ['no', 'No'],
            ['unsure', 'Not sure'],
          ]}
          onChange={(v) => set('care_received', v)}
        />

        <Choice
          name="internal"
          legend="Have you already appealed to the plan?"
          value={s.internal_appeal}
          options={[
            ['not_yet', 'Not yet'],
            ['waiting', 'Yes, waiting'],
            ['decided', 'Yes, it was denied'],
          ]}
          onChange={(v) => set('internal_appeal', v)}
        />

        {s.internal_appeal === 'decided' && (
          <div className="mini-field">
            <label htmlFor="decision-date">When did you receive the appeal decision?</label>
            <input
              id="decision-date"
              type="date"
              max={today()}
              value={s.final_decision_date ?? ''}
              onChange={(e) => set('final_decision_date', e.target.value || null)}
            />
          </div>
        )}
      </div>

      {(problem || error) && (
        <p className="form-error" role="alert">
          {problem ?? error}
        </p>
      )}

      <button type="submit" className="btn btn-primary" disabled={submitting}>
        {submitting ? 'Building…' : 'Show my action plan'} <Icon name="arrow" size={18} />
      </button>
    </form>
  );
}
