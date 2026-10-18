import type { ExtractedField } from './api';
import { citationId } from '../../core/lib/highlight';
import { Icon } from '../../core/components/Icon';

interface Props {
  field: ExtractedField;
  activeId: string | null;
  onCite: (id: string) => void;
}

const MULTI_VALUE = new Set(['appeal_instructions', 'reference_numbers', 'appeal_deadline']);

export function FieldCard({ field, activeId, onCite }: Props) {
  const found = field.status === 'found';
  const headingId = `field-${field.key}`;
  return (
    <article className={found ? 'field-card' : 'field-card field-missing'} aria-labelledby={headingId}>
      <header className="field-head">
        <h3 id={headingId}>{field.label}</h3>
        <span className={found ? 'status status-found' : 'status status-missing'}>{found ? 'Found in letter' : 'Not in this letter'}</span>
      </header>

      {found &&
        (MULTI_VALUE.has(field.key) && field.values.length > 1 ? (
          <ul className="field-values">
            {field.values.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        ) : (
          <p className="field-value">{field.value}</p>
        ))}

      {field.note && <p className="field-note">{field.note}</p>}
      {found && field.confidence === 'medium' && (
        <p className="field-note">
          <Icon name="alert" size={14} /> Identified from the letter’s layout. Double-check it against the highlighted passage.
        </p>
      )}

      {field.citations.length > 0 && (
        <div className="cite-buttons" role="group" aria-label={`Where this appears in your letter`}>
          {field.citations.map((c, i) => {
            const id = citationId(field.key, i);
            return (
              <button
                key={id}
                type="button"
                className={activeId === id ? 'cite-button active' : 'cite-button'}
                aria-pressed={activeId === id}
                onClick={() => onCite(id)}
              >
                <Icon name="doc" size={14} /> Page {c.page}
                {field.citations.length > 1 ? ` · passage ${i + 1}` : ''}
              </button>
            );
          })}
        </div>
      )}
    </article>
  );
}
